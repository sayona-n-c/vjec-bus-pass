import uuid
import json
import functools
import qrcode
import io
import base64
from datetime import date, datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.conf import settings
from django.db.models import Count

from .models import Route, Bus, UserProfile, BusPass, Attendance, GPSLocation, BusCoordinator, BoardingPoint
from .forms import StudentRegistrationForm, BusPassBookingForm, FacultyReserveForm


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def auth_required(view_func):
    """
    Secure drop-in for @login_required:
    - Applies @never_cache to prevent caching of protected pages
    - Flashes '🔒 Authentication required' warning before redirecting
    - Preserves all function metadata via functools.wraps
    """
    @never_cache
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(
                request,
                '🔒 Authentication required. Please log in to continue.'
            )
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        return view_func(request, *args, **kwargs)
    return wrapper

def is_within_registration_window():
    """Time-based window removed. Booking is available 24/7."""
    return True


def generate_qr_image_base64(data: str) -> str:
    """Generate QR code image and return as base64 string."""
    qr = qrcode.QRCode(version=1, box_size=6, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def is_admin(user):
    return user.is_authenticated and (user.is_staff or
           (hasattr(user, 'profile') and user.profile.role == 'admin'))



def calculate_fare(raw_fare: int) -> int:
    """
    Clamp the fare to ₹15–₹150 range, then round to nearest ₹10.
    Zero / negative raw fares are treated as 15 (minimum).
    """
    value = max(15, min(150, max(1, int(raw_fare))))  # ensure >= 1 before clamping
    if value <= 15:
        return 15
    return round(value / 10) * 10


# ──────────────────────────────────────────────
# AUTH VIEWS
# ──────────────────────────────────────────────

def register_view(request):
    """User registration — open at all times."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data.get('vml_no', '').upper()
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            # Update or create profile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.vml_no = form.cleaned_data.get('vml_no', '')
            profile.role = form.cleaned_data.get('role', 'student')
            profile.phone = form.cleaned_data.get('phone', '')
            profile.department = form.cleaned_data.get('department', '')
            # Only set student_type for students; faculty don't commute daily
            if profile.role == 'student':
                profile.student_type = form.cleaned_data.get('student_type', 'hosteler')
            profile.save()

            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}! Your account has been created.')
            return redirect('dashboard')
    else:
        form = StudentRegistrationForm()

    return render(request, 'core/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        # Redirect drivers to their dashboard
        if hasattr(request.user, 'profile') and request.user.profile.role == 'driver':
            return redirect('driver_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        # Normalize: strip whitespace and uppercase so 'vml23cs100' == 'VML23CS100'
        raw_username = request.POST.get('username', '').strip().upper()
        password = request.POST.get('password', '')

        user = authenticate(request, username=raw_username, password=password)

        # Case-insensitive fallback: try matching against stored usernames
        if user is None and raw_username:
            from django.contrib.auth.models import User as AuthUser
            try:
                matched = AuthUser.objects.get(username__iexact=raw_username)
                user = authenticate(request, username=matched.username, password=password)
            except AuthUser.DoesNotExist:
                user = None

        if user is not None:
            if not user.is_active:
                messages.error(request, '⛔ Your account is inactive. Please contact the administrator.')
            else:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                # Redirect drivers to driver dashboard
                if hasattr(user, 'profile') and user.profile.role == 'driver':
                    return redirect('driver_dashboard')
                return redirect(request.GET.get('next', 'dashboard'))
        else:
            messages.error(request, '❌ Invalid VML Number or Password. Please try again.')

    return render(request, 'core/login.html')


def logout_view(request):
    """Strict secure logout: terminate session, set no-cache, redirect to login.
    If the user is a driver, stop GPS tracking on their assigned bus."""
    # Privacy: stop tracking on assigned bus before logout
    if hasattr(request.user, 'profile') and request.user.profile.role == 'driver':
        Bus.objects.filter(driver=request.user, is_tracking=True).update(
            is_tracking=False
        )
    logout(request)               # 1. deauthenticate + clear auth keys from session
    request.session.flush()       # 2. delete session from DB + expire cookie on client
    response = redirect('login')
    # 3. Force browser not to cache this redirect or any previously seen auth pages
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma']         = 'no-cache'
    response['Expires']        = '0'
    messages.info(request, '🔒 You have been logged out. Your session has been terminated.')
    return response


# ──────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────

@auth_required
def dashboard_view(request):
    profile = getattr(request.user, 'profile', None)

    # ── Driver Dashboard: show driver-specific content ──
    if profile and profile.role == 'driver':
        assigned_bus = Bus.objects.filter(driver=request.user, is_active=True).select_related('route').first()
        all_buses = Bus.objects.filter(is_active=True).select_related('route').order_by('bus_number')
        boarding_points = BoardingPoint.objects.all().order_by('fare', 'name')
        return render(request, 'core/driver_home.html', {
            'profile': profile,
            'assigned_bus': assigned_bus,
            'all_buses': all_buses,
            'boarding_points': boarding_points,
            'active_bus_count': all_buses.count(),
        })

    active_pass = BusPass.objects.filter(user=request.user, status='active').first()
    pending_pass = BusPass.objects.filter(user=request.user, status='pending').first()
    recent_passes = BusPass.objects.filter(user=request.user).order_by('-created_at')[:5]
    active_buses = Bus.objects.filter(is_active=True).count()
    active_routes = Route.objects.filter(is_active=True).count()

    context = {
        'profile': profile,
        'active_pass': active_pass,
        'pending_pass': pending_pass,
        'recent_passes': recent_passes,
        'active_buses': active_buses,
        'active_routes': active_routes,
    }
    return render(request, 'core/dashboard.html', context)


# ──────────────────────────────────────────────
# ROUTES & BUSES
# ──────────────────────────────────────────────

@auth_required
def routes_view(request):
    routes = Route.objects.filter(is_active=True).prefetch_related('buses').order_by('name')
    return render(request, 'core/routes.html', {'routes': routes})


@auth_required
def bus_list_view(request, route_id):
    route = get_object_or_404(Route, pk=route_id, is_active=True)
    buses = Bus.objects.filter(route=route, is_active=True).order_by('bus_number')
    return render(request, 'core/bus_list.html', {'route': route, 'buses': buses})


@auth_required
def bus_detail_view(request, bus_id):
    bus = get_object_or_404(Bus, pk=bus_id, is_active=True)
    gps = GPSLocation.objects.filter(bus=bus).order_by('-timestamp').first()
    coordinator = getattr(bus, 'coordinator', None)
    return render(request, 'core/bus_detail.html', {
        'bus': bus,
        'gps': gps,
        'coordinator': coordinator,
    })


# ──────────────────────────────────────────────
# BOOKING & PAYMENT
# ──────────────────────────────────────────────

@auth_required
def booking_view(request, bus_id):
    # ── RBAC: Admins cannot book passes ──
    if is_admin(request.user):
        messages.error(request, 'Admins cannot book bus passes.')
        return redirect('admin_dashboard')

    # ── RBAC: Day Scholars do not need a bus pass ──
    profile = getattr(request.user, 'profile', None)
    if profile and profile.student_type == 'day_scholar':
        messages.info(request, '🏠 Day Scholars do not require a bus pass. Use the QR attendance system to mark your daily boarding.')
        return redirect('dashboard')

    bus = get_object_or_404(Bus, pk=bus_id, is_active=True)

    # ── Seat availability ──
    if not bus.is_available:
        messages.error(request, f'Bus {bus.bus_number} is fully booked. No seats available.')
        return redirect('bus_detail', bus_id=bus_id)

    # ── Already has active pass ──
    existing = BusPass.objects.filter(user=request.user, status='active').first()
    if existing:
        messages.warning(request, 'You already have an active bus pass.')
        return redirect('view_pass', pass_id=existing.pass_id)

    if request.method == 'POST':
        form = BusPassBookingForm(request.POST, bus=bus)
        if form.is_valid():
            bp_obj = form.cleaned_data['boarding_point']  # BoardingPoint instance
            fare   = calculate_fare(bp_obj.fare)          # ₹15–₹150 clamped + rounded

            bus_pass = BusPass.objects.create(
                user=request.user,
                bus=bus,
                route=bus.route,
                boarding_point=bp_obj.name,
                boarding_point_ref=bp_obj,
                amount_paid=fare,
                status='pending',
                valid_from=date.today(),
                valid_until=date.today(),  # Daily pass – valid until end of booking day
            )
            return redirect('payment', pass_id=bus_pass.pass_id)
    else:
        form = BusPassBookingForm(bus=bus)

    return render(request, 'core/booking.html', {'bus': bus, 'form': form})


@auth_required
def payment_view(request, pass_id):
    """Payment page: student scans UPI QR then uploads screenshot as proof.
    The pass stays 'pending' until an admin confirms it."""
    # ── RBAC: Admins cannot access student payment ──
    if is_admin(request.user):
        messages.error(request, 'Admins do not have access to the payment page.')
        return redirect('admin_dashboard')

    bus_pass = get_object_or_404(BusPass, pass_id=pass_id, user=request.user, status='pending')
    payment_link = settings.PAYMENT_LINK + f'?ref={bus_pass.pass_id_short}&amt={bus_pass.amount_paid}'

    uploaded = False
    if request.method == 'POST':
        screenshot = request.FILES.get('payment_screenshot')
        txn_notes = request.POST.get('payment_notes', '').strip()
        if screenshot:
            bus_pass.payment_screenshot = screenshot
            if txn_notes:
                bus_pass.payment_notes = txn_notes
            bus_pass.save(update_fields=['payment_screenshot', 'payment_notes'])
            uploaded = True
            messages.success(request, '✅ Payment screenshot uploaded! An admin will verify and activate your pass shortly.')
        else:
            messages.error(request, 'Please select a screenshot file to upload.')

    return render(request, 'core/payment.html', {
        'bus_pass': bus_pass,
        'payment_link': payment_link,
        'uploaded': uploaded,
        'already_uploaded': bool(bus_pass.payment_screenshot),
    })


@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def payment_confirm_view(request, pass_id):
    """Admin-only: confirm a student's payment and activate their bus pass."""
    bus_pass = get_object_or_404(BusPass, pass_id=pass_id)
    if bus_pass.status == 'pending':
        bus_pass.status = 'active'
        bus_pass.save(update_fields=['status'])
        # Increment occupancy on the bus
        if bus_pass.bus and bus_pass.bus.current_occupancy < bus_pass.bus.capacity:
            bus_pass.bus.current_occupancy += 1
            bus_pass.bus.save(update_fields=['current_occupancy'])
        messages.success(request, f'✅ Pass {bus_pass.pass_id_short} activated for {bus_pass.user.get_full_name() or bus_pass.user.username}.')
    else:
        messages.warning(request, f'Pass {bus_pass.pass_id_short} is already {bus_pass.status}.')
    return redirect('admin_dashboard')


@auth_required
def view_pass_view(request, pass_id):
    bus_pass = get_object_or_404(BusPass, pass_id=pass_id)
    # Only allow user or admin to view
    if bus_pass.user != request.user and not is_admin(request.user):
        messages.error(request, 'You do not have permission to view this pass.')
        return redirect('dashboard')

    profile = getattr(bus_pass.user, 'profile', None)

    return render(request, 'core/digital_pass.html', {
        'bus_pass': bus_pass,
        'profile': profile,
        'now': timezone.localtime(timezone.now()),
    })


@auth_required
def my_passes_view(request):
    passes = BusPass.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'core/my_passes.html', {'passes': passes})


# ──────────────────────────────────────────────
# QR ATTENDANCE
# ──────────────────────────────────────────────

@auth_required
def generate_qr_view(request, bus_id):
    """Generate a QR code for the logged-in user to scan when boarding a bus."""
    bus = get_object_or_404(Bus, pk=bus_id, is_active=True)
    profile = getattr(request.user, 'profile', None)
    if not profile:
        messages.error(request, 'Profile not found.')
        return redirect('dashboard')

    qr_data = f"SCAN:{profile.qr_token}:BUS:{bus.bus_number}:BUSID:{bus.id}"
    qr_image = generate_qr_image_base64(qr_data)
    return render(request, 'core/qr_code.html', {
        'bus': bus,
        'qr_image': qr_image,
        'profile': profile,
    })


@csrf_exempt
@require_POST
def scan_qr_view(request):
    """
    API endpoint: receives QR scan data, records attendance, decrements seat.
    POST body: { "qr_data": "SCAN:<token>:BUS:<bus_number>:BUSID:<bus_id>" }
    """
    try:
        body = json.loads(request.body)
        qr_data = body.get('qr_data', '')
        parts = qr_data.split(':')
        # Expected format: SCAN:<token>:BUS:<bus_number>:BUSID:<bus_id>
        if len(parts) < 6 or parts[0] != 'SCAN':
            return JsonResponse({'success': False, 'error': 'Invalid QR data format'}, status=400)

        token = parts[1]
        bus_id = parts[5]

        profile = UserProfile.objects.filter(qr_token=token).first()
        if not profile:
            return JsonResponse({'success': False, 'error': 'Invalid user token'}, status=404)

        bus = Bus.objects.filter(pk=bus_id, is_active=True).first()
        if not bus:
            return JsonResponse({'success': False, 'error': 'Bus not found'}, status=404)

        # Prevent duplicate scan on same date
        today = date.today()
        if Attendance.objects.filter(user=profile.user, bus=bus, date=today).exists():
            return JsonResponse({'success': False, 'error': 'Already scanned today for this bus'}, status=409)

        if profile.is_hosteler:
            # Get active pass for this user
            bus_pass = BusPass.objects.filter(user=profile.user, status='active').first()
            if not bus_pass:
                return JsonResponse({'success': False, 'error': 'No active bus pass found. Please book a pass.'}, status=403)
            return JsonResponse({
                'success': True,
                'message': 'Pass already active, no scan required.',
                'available_seats': bus.available_seats,
                'student_name': profile.display_name,
                'bus_number': bus.bus_number,
            })

        if profile.is_day_scholar:
            if bus.available_seats <= 0:
                return JsonResponse({'success': False, 'error': 'Bus is full, no seats available.'}, status=409)

            # Create attendance record
            Attendance.objects.create(
                user=profile.user,
                bus=bus,
                bus_pass=None,
            )
            # increment occupancy explicitly
            bus.current_occupancy += 1
            bus.save(update_fields=['current_occupancy'])

        bus.refresh_from_db()
        return JsonResponse({
            'success': True,
            'message': f'Welcome aboard! {profile.display_name} scanned for Bus {bus.bus_number}',
            'available_seats': bus.available_seats,
            'student_name': profile.display_name,
            'bus_number': bus.bus_number,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON in request body'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ──────────────────────────────────────────────
# GPS / MAP
# ──────────────────────────────────────────────

@auth_required
def map_view(request):
    buses = Bus.objects.filter(is_active=True).select_related('route')
    buses_with_gps = []
    for bus in buses:
        gps = GPSLocation.objects.filter(bus=bus).order_by('-timestamp').first()
        buses_with_gps.append({'bus': bus, 'gps': gps})
    return render(request, 'core/map.html', {'buses_with_gps': buses_with_gps})


@csrf_exempt
@require_POST
def gps_update_view(request):
    """API endpoint for GPS devices to push location data."""
    try:
        body = json.loads(request.body)
        bus_number = body.get('bus_number')
        lat = body.get('latitude')
        lng = body.get('longitude')
        speed = body.get('speed', 0.0)

        bus = Bus.objects.filter(bus_number=bus_number, is_active=True).first()
        if not bus:
            return JsonResponse({'success': False, 'error': 'Bus not found'}, status=404)

        GPSLocation.objects.create(bus=bus, latitude=lat, longitude=lng, speed=speed)
        return JsonResponse({'success': True, 'message': 'GPS updated'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_bus_locations_view(request):
    """Returns JSON of all active bus GPS positions for map polling.
    Uses the live lat/lng fields on Bus for fastest response."""
    buses = Bus.objects.filter(
        is_active=True, is_tracking=True,
        latitude__isnull=False, longitude__isnull=False
    ).select_related('route')
    data = []
    for bus in buses:
        latest_gps = GPSLocation.objects.filter(bus=bus).order_by('-timestamp').first()
        data.append({
            'bus_id': bus.id,
            'bus_number': bus.bus_number,
            'route': bus.route.name if bus.route else '',
            'lat': float(bus.latitude),
            'lng': float(bus.longitude),
            'is_tracking': bus.is_tracking,
            'speed': round(latest_gps.speed, 1) if latest_gps else 0,
            'updated': latest_gps.timestamp.strftime('%I:%M %p') if latest_gps else '',
        })
    return JsonResponse({'buses': data})


# ──────────────────────────────────────────────
# ADMIN PANEL
# ──────────────────────────────────────────────

@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_dashboard_view(request):
    buses = sorted(
        Bus.objects.all().select_related('route'),
        key=lambda b: int(''.join(filter(str.isdigit, b.bus_number)) or 0)
    )

    routes = Route.objects.all()
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    passes = BusPass.objects.select_related('user', 'bus', 'route').order_by('-created_at')[:50]
    boarding_points = BoardingPoint.objects.all().order_by('fare', 'name')

    # Attendance (today by default, or filtered)
    att_filter_date = request.GET.get('att_date', str(date.today()))
    try:
        att_dt = date.fromisoformat(att_filter_date)
    except ValueError:
        att_dt = date.today()
    attendance_records = Attendance.objects.filter(date=att_dt).select_related(
        'user', 'bus', 'bus_pass'
    ).order_by('-scanned_at')

    # GPS Logs (today by default, optional bus filter)
    gps_filter_date = request.GET.get('gps_date', str(date.today()))
    gps_bus_id = request.GET.get('gps_bus', '')
    try:
        gps_dt = date.fromisoformat(gps_filter_date)
    except ValueError:
        gps_dt = date.today()
    gps_qs = GPSLocation.objects.filter(timestamp__date=gps_dt).select_related('bus')
    if gps_bus_id:
        gps_qs = gps_qs.filter(bus_id=gps_bus_id)
    gps_logs = gps_qs.order_by('-timestamp')[:100]

    stats = {
        'total_buses': Bus.objects.count(),
        'active_buses': Bus.objects.filter(is_active=True).count(),
        'total_routes': routes.count(),
        'total_users': users.count(),
        'total_passes': BusPass.objects.count(),
        'active_passes': BusPass.objects.filter(status='active').count(),
        'today_attendance': Attendance.objects.filter(date=date.today()).count(),
    }
    return render(request, 'core/admin_dashboard.html', {
        'buses': buses,
        'routes': routes,
        'users': users,
        'passes': passes,
        'stats': stats,
        'boarding_points': boarding_points,
        'attendance_records': attendance_records,
        'att_filter_date': att_dt,
        'gps_logs': gps_logs,
        'gps_filter_date': gps_dt,
        'gps_bus_id': gps_bus_id,
    })


@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_edit_bus_view(request, bus_id):
    """Admin frontend page: edit bus information and boarding point fares."""
    bus = get_object_or_404(Bus, pk=bus_id)
    routes = Route.objects.filter(is_active=True)
    coordinator = getattr(bus, 'coordinator', None)

    # Get boarding points relevant to this bus's route
    if bus.route:
        stops = [s.strip().upper() for s in bus.route.get_stops_list()]
        boarding_points = BoardingPoint.objects.filter(name__in=stops).order_by('fare', 'name')
        if not boarding_points.exists():
            boarding_points = BoardingPoint.objects.all().order_by('fare', 'name')
    else:
        boarding_points = BoardingPoint.objects.all().order_by('fare', 'name')

    if request.method == 'POST':
        # ── Save Bus Info ──
        bus.bus_number = request.POST.get('bus_number', bus.bus_number).strip()
        bus.capacity = int(request.POST.get('capacity', bus.capacity))
        bus.bus_type = request.POST.get('bus_type', bus.bus_type)
        bus.is_active = request.POST.get('is_active') == 'on'
        route_id = request.POST.get('route')
        bus.route = Route.objects.filter(pk=route_id).first() if route_id else None
        bus.save()

        # ── Save Boarding Point Fares ──
        for bp in boarding_points:
            fare_key = f'fare_{bp.id}'
            if fare_key in request.POST:
                new_fare = int(request.POST[fare_key])
                new_fare = max(15, min(150, new_fare))  # clamp ₹15–₹150
                if bp.fare != new_fare:
                    bp.fare = new_fare
                    bp.save(update_fields=['fare'])

        # ── Save Coordinator Info ──
        if coordinator is not None:
            coordinator.name = request.POST.get('coord_name', coordinator.name).strip()  # type: ignore[union-attr]
            coordinator.staff_id = request.POST.get('coord_staff_id', coordinator.staff_id).strip()  # type: ignore[union-attr]
            coordinator.contact = request.POST.get('coord_contact', coordinator.contact or '').strip()  # type: ignore[union-attr]
            coordinator.save()  # type: ignore[union-attr]

        messages.success(request, f'✅ Bus {bus.bus_number} updated successfully.')
        return redirect('bus_detail', bus_id=bus.id)

    return render(request, 'core/admin_edit_bus.html', {
        'bus': bus,
        'routes': routes,
        'boarding_points': boarding_points,
        'coordinator': coordinator,
    })


@auth_required
@user_passes_test(is_admin)
def admin_reset_occupancy_view(request, bus_id):
    """Reset current occupancy to 0 (end of day)."""
    bus = get_object_or_404(Bus, pk=bus_id)
    bus.current_occupancy = 0
    bus.save()
    messages.success(request, f'Bus {bus.bus_number} occupancy reset to 0.')
    return redirect('admin_dashboard')


# ──────────────────────────────────────────────
# PHYSICAL BUS QR SCAN → MARK ATTENDANCE
# ──────────────────────────────────────────────

@auth_required
def mark_attendance_view(request, bus_id):
    """
    Endpoint embedded in the PHYSICAL QR code sticker placed inside each bus.
    When a student scans the bus QR with their phone:
      1. Login is verified (redirect to login if not authenticated).
      2. Active bus pass for this bus is confirmed.
      3. Attendance is recorded (once per bus per day).
      4. Bus current_occupancy is incremented.
    """
    bus = get_object_or_404(Bus, pk=bus_id, is_active=True)
    today = date.today()
    now_local = timezone.localtime(timezone.now())

    # ── Already marked today? ──
    already = Attendance.objects.filter(
        user=request.user, bus=bus, date=today
    ).first()
    if already:
        return render(request, 'core/attendance_result.html', {
            'bus': bus,
            'status': 'already_marked',
            'scanned_at': already.scanned_at,
            'message': f'You have already boarded Bus {bus.bus_number} today.',
        })

    profile = getattr(request.user, 'profile', None)
    
    if profile and profile.is_hosteler:
        # ── Check for active pass ──
        active_pass = BusPass.objects.filter(user=request.user, status='active').first()
        if not active_pass:
            return render(request, 'core/attendance_result.html', {
                'bus': bus,
                'status': 'no_pass',
                'message': 'No active bus pass found. Please book a pass before boarding.',
            })
        return render(request, 'core/attendance_result.html', {
            'bus': bus,
            'status': 'already_marked',
            'message': 'Pass already active, no scan required.',
            'bus_pass': active_pass,
        })

    if profile and profile.is_day_scholar:
        if bus.available_seats <= 0:
            return render(request, 'core/attendance_result.html', {
                'bus': bus,
                'status': 'no_pass',
                'message': 'This bus is fully occupied.',
            })

        # ── Mark attendance ──
        attendance = Attendance.objects.create(
            user=request.user,
            bus=bus,
            bus_pass=None,
        )

        # ── Decrement available seats ──
        bus.current_occupancy += 1
        bus.save(update_fields=['current_occupancy'])
        active_pass = None

    return render(request, 'core/attendance_result.html', {
        'bus': bus,
        'bus_pass': active_pass,
        'status': 'success',
        'scanned_at': attendance.scanned_at,
        'message': f'Attendance marked! Welcome aboard Bus {bus.bus_number}.',
        'available_seats': bus.available_seats,
    })


# ──────────────────────────────────────────────
# AJAX: Boarding Points for a Given Bus
# ──────────────────────────────────────────────

@auth_required
def api_boarding_points(request, bus_id):
    """
    AJAX endpoint: returns JSON list of boarding points for a bus route.
    Used by booking form dynamic dropdown.
    """
    bus = get_object_or_404(Bus, pk=bus_id, is_active=True)
    if bus.route:
        stops = [s.strip().upper() for s in bus.route.get_stops_list()]
        qs = BoardingPoint.objects.filter(name__in=stops).order_by('fare', 'name')
        if not qs.exists():
            qs = BoardingPoint.objects.all().order_by('fare', 'name')
    else:
        qs = BoardingPoint.objects.all().order_by('fare', 'name')

    data = [{'id': bp.id, 'name': bp.name, 'fare': bp.fare} for bp in qs]
    return JsonResponse({'boarding_points': data})


# ──────────────────────────────────────────────
# BUS QR CODE GENERATION (Admin – For Printing)
# ──────────────────────────────────────────────

@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def bus_qr_view(request, bus_id):
    """
    Generate a printable QR code for the physical bus sticker.
    Encodes the mark-attendance URL for this bus.
    Printed and placed inside the bus for students to scan.
    """
    bus = get_object_or_404(Bus, pk=bus_id)
    qr_data = request.build_absolute_uri(f'/mark-attendance/{bus.id}/')
    qr_image = generate_qr_image_base64(qr_data)
    return render(request, 'core/bus_qr_print.html', {
        'bus': bus,
        'qr_image': qr_image,
        'qr_data': qr_data,
    })


# ──────────────────────────────────────────────
# STUDENT: CAMERA → SCAN BUS QR FOR ATTENDANCE
# ──────────────────────────────────────────────

@auth_required
def scan_attendance_view(request):
    """
    Student-facing page that opens the device camera to scan the bus QR sticker.
    Uses jsQR library to decode QR from camera feed, then redirects to mark-attendance.
    """
    if is_admin(request.user):
        messages.error(request, 'Admins do not take attendance via QR scan.')
        return redirect('admin_dashboard')
    return render(request, 'core/scan_attendance.html')


# ──────────────────────────────────────────────
# DRIVER GPS INTERFACE
# ──────────────────────────────────────────────

def driver_login_view(request):
    """Driver-specific login page."""
    if request.user.is_authenticated and hasattr(request.user, 'profile') and \
            request.user.profile.role == 'driver':
        return redirect('driver_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user and hasattr(user, 'profile') and user.profile.role == 'driver':
            login(request, user)
            return redirect('driver_dashboard')
        else:
            messages.error(request, 'Invalid credentials or not a driver account.')
    return render(request, 'core/driver_login.html')


@auth_required
def driver_dashboard_view(request):
    """Driver's trip control page — start/stop GPS tracking.
    Only shows the bus assigned to this driver (no bus selector)."""
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'driver'):
        # Also allow staff/admin to view
        if not is_admin(request.user):
            messages.error(request, 'Access denied. Driver accounts only.')
            return redirect('dashboard')

    # Find bus assigned to this driver via FK
    assigned_bus = Bus.objects.filter(
        driver=request.user, is_active=True
    ).first()

    if not assigned_bus and not is_admin(request.user):
        messages.warning(request, 'No bus is assigned to your account. Please contact admin.')

    return render(request, 'core/driver_dashboard.html', {
        'assigned_bus': assigned_bus,
    })


@csrf_exempt
@require_POST
def driver_gps_push_view(request):
    """
    Called by the driver's browser Geolocation API every 30 seconds.
    POST: { bus_id, latitude, longitude, speed, action }
    Stores a GPSLocation record and updates the Bus live fields.
    action='start' → set is_tracking=True
    action='stop'  → set is_tracking=False, clear lat/lng
    """
    try:
        body = json.loads(request.body)
        bus_id  = body.get('bus_id')
        lat     = body.get('latitude')
        lng     = body.get('longitude')
        speed   = body.get('speed', 0.0)
        action  = body.get('action', 'update')  # start / stop / update

        bus = Bus.objects.filter(pk=bus_id, is_active=True).first()
        if not bus:
            return JsonResponse({'success': False, 'error': 'Bus not found'}, status=404)

        if action == 'stop':
            bus.is_tracking = False
            bus.latitude = None
            bus.longitude = None
            bus.save(update_fields=['is_tracking', 'latitude', 'longitude'])
            return JsonResponse({'success': True, 'message': 'Tracking stopped'})

        # start or update
        bus.latitude = lat
        bus.longitude = lng
        bus.is_tracking = True
        bus.save(update_fields=['latitude', 'longitude', 'is_tracking'])

        GPSLocation.objects.create(bus=bus, latitude=lat, longitude=lng, speed=speed)
        return JsonResponse({
            'success': True,
            'message': f'GPS updated for Bus {bus.bus_number}',
            'available_seats': bus.available_seats,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_add_driver_view(request):
    """Admin: create a Driver user account and optionally assign to a bus."""
    if request.method == 'POST':
        driver_name = request.POST.get('driver_name', '').strip()
        raw_username = request.POST.get('driver_username', '').strip()
        password = request.POST.get('driver_password', '').strip()
        bus_id = request.POST.get('driver_bus', '')

        if not raw_username or not password or not driver_name:
            messages.error(request, 'Driver name, username, and password are required.')
            return redirect('admin_dashboard')

        # Auto-prefix 'd' to driver username if not already
        username = raw_username if raw_username.lower().startswith('d') else f'd{raw_username}'

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists.')
            return redirect('admin_dashboard')

        # Create user
        user = User.objects.create_user(
            username=username, password=password,
            first_name=driver_name.split()[0] if driver_name else username,
            last_name=' '.join(driver_name.split()[1:]) if len(driver_name.split()) > 1 else '',
        )
        # Create profile with driver role (signal may have already created one)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = 'driver'
        profile.save(update_fields=['role'])

        # Assign to bus if selected
        if bus_id:
            bus = Bus.objects.filter(pk=bus_id).first()
            if bus:
                bus.driver = user
                bus.driver_name = driver_name
                bus.save(update_fields=['driver', 'driver_name'])
                messages.success(request, f'✅ Driver "{driver_name}" created and assigned to Bus {bus.bus_number}.')
            else:
                messages.success(request, f'✅ Driver "{driver_name}" created (bus not found).')
        else:
            messages.success(request, f'✅ Driver "{driver_name}" created (no bus assigned).')

    return redirect('admin_dashboard')


@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def faculty_reserve_view(request):
    """Admin: create a ₹0 active bus pass for a faculty/staff seat reservation."""
    buses = Bus.objects.filter(is_active=True).select_related('route').order_by('bus_number')

    if request.method == 'POST':
        form = FacultyReserveForm(request.POST)
        if form.is_valid():
            bus = form.cleaned_data['bus']
            faculty_name = form.cleaned_data['faculty_name'].strip()
            bp_obj = form.cleaned_data.get('boarding_point')  # optional

            # Create a ₹0 active pass for the faculty member under the admin's account
            bus_pass = BusPass.objects.create(
                user=request.user,
                bus=bus,
                route=bus.route,
                boarding_point=bp_obj.name if bp_obj else '—',
                boarding_point_ref=bp_obj if bp_obj else None,
                amount_paid=0,
                status='active',
                valid_from=date.today(),
                valid_until=date.today(),
                notes=f'Faculty Reserve – {faculty_name}',
            )

            # Decrement available seats
            if bus.current_occupancy < bus.capacity:
                bus.current_occupancy += 1
                bus.save(update_fields=['current_occupancy'])

            messages.success(
                request,
                f'✅ Seat reserved for {faculty_name} on Bus {bus.bus_number}. Pass ID: {bus_pass.pass_id_short}'
            )
            return redirect('admin_dashboard')
    else:
        form = FacultyReserveForm()

    return render(request, 'core/faculty_reserve.html', {
        'form': form,
        'buses': buses,
    })


@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_attendance_view(request):
    """Admin view: list all attendance records with optional date filter."""
    filter_date = request.GET.get('date', str(date.today()))
    try:
        filter_dt = date.fromisoformat(filter_date)
    except ValueError:
        filter_dt = date.today()

    records = Attendance.objects.filter(date=filter_dt).select_related(
        'user', 'bus', 'bus_pass'
    ).order_by('-scanned_at')

    buses = Bus.objects.filter(is_active=True).order_by('bus_number')
    return render(request, 'core/admin_attendance.html', {
        'records': records,
        'filter_date': filter_dt,
        'buses': buses,
        'today': date.today(),
    })


# ──────────────────────────────────────────────
# ADMIN CRUD: BUSES
# ──────────────────────────────────────────────

@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_add_bus_view(request):
    """Admin: add a new bus. Supports selecting existing route OR typing a new route name."""
    if request.method == 'POST':
        bus_number = request.POST.get('bus_number', '').strip()
        capacity = int(request.POST.get('capacity', 49))
        bus_type = request.POST.get('bus_type', 'college')
        route_id = request.POST.get('route', '')
        new_route_name = request.POST.get('new_route', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        if not bus_number:
            messages.error(request, 'Bus number is required.')
            return redirect('admin_dashboard')

        if Bus.objects.filter(bus_number=bus_number).exists():
            messages.error(request, f'Bus {bus_number} already exists.')
            return redirect('admin_dashboard')

        # If admin typed a new route name, create it
        if new_route_name:
            route, created = Route.objects.get_or_create(
                name=new_route_name,
                defaults={'is_active': True}
            )
            if created:
                messages.info(request, f'🗺️ New route "{new_route_name}" created.')
        elif route_id:
            route = Route.objects.filter(pk=route_id).first()
        else:
            route = None

        Bus.objects.create(
            bus_number=bus_number,
            capacity=capacity,
            bus_type=bus_type,
            route=route,
            is_active=is_active,
        )
        messages.success(request, f'✅ Bus {bus_number} added successfully.')
    return redirect('admin_dashboard')


@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_delete_bus_view(request, bus_id):
    """Admin: delete a bus."""
    if request.method == 'POST':
        bus = get_object_or_404(Bus, pk=bus_id)
        bus_number = bus.bus_number
        bus.delete()
        messages.success(request, f'🗑️ Bus {bus_number} deleted.')
    return redirect('admin_dashboard')


# ──────────────────────────────────────────────
# ADMIN CRUD: ROUTES
# ──────────────────────────────────────────────

@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_add_route_view(request):
    """Admin: add a new route."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        stops_raw = request.POST.get('stops', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        if not name:
            messages.error(request, 'Route name is required.')
            return redirect('admin_dashboard')

        stops = [s.strip() for s in stops_raw.split(',') if s.strip()] if stops_raw else []
        Route.objects.create(
            name=name,
            description=description,
            stops=stops,
            is_active=is_active,
        )
        messages.success(request, f'✅ Route "{name}" added successfully.')
    return redirect('admin_dashboard')


@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_edit_route_view(request, route_id):
    """Admin: edit a route."""
    route = get_object_or_404(Route, pk=route_id)
    if request.method == 'POST':
        route.name = request.POST.get('name', route.name).strip()
        route.description = request.POST.get('description', route.description).strip()
        stops_raw = request.POST.get('stops', '').strip()
        route.stops = [s.strip() for s in stops_raw.split(',') if s.strip()] if stops_raw else []
        route.is_active = request.POST.get('is_active') == 'on'
        route.save()
        messages.success(request, f'✅ Route "{route.name}" updated successfully.')
        return redirect('admin_dashboard')

    # GET: render edit form
    return render(request, 'core/admin_edit_route.html', {
        'route': route,
    })


@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_delete_route_view(request, route_id):
    """Admin: delete a route."""
    if request.method == 'POST':
        route = get_object_or_404(Route, pk=route_id)
        name = route.name
        route.delete()
        messages.success(request, f'🗑️ Route "{name}" deleted.')
    return redirect('admin_dashboard')


# ──────────────────────────────────────────────
# ADMIN CRUD: USERS
# ──────────────────────────────────────────────

@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_edit_user_view(request, user_id):
    """Admin: edit user profile (role, department, phone)."""
    target_user = get_object_or_404(User, pk=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    if request.method == 'POST':
        target_user.first_name = request.POST.get('first_name', target_user.first_name).strip()
        target_user.last_name = request.POST.get('last_name', target_user.last_name).strip()
        target_user.email = request.POST.get('email', target_user.email).strip()
        target_user.save()

        profile.role = request.POST.get('role', profile.role)
        profile.department = request.POST.get('department', profile.department).strip()
        profile.phone = request.POST.get('phone', profile.phone).strip()
        profile.vml_no = request.POST.get('vml_no', profile.vml_no or '').strip() or profile.vml_no
        profile.save()

        messages.success(request, f'✅ User "{target_user.get_full_name() or target_user.username}" updated.')
        return redirect('admin_dashboard')

    return render(request, 'core/admin_edit_user.html', {
        'target_user': target_user,
        'profile': profile,
    })


@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_delete_user_view(request, user_id):
    """Admin: delete a user."""
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=user_id)
        if target_user == request.user:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('admin_dashboard')
        name = target_user.get_full_name() or target_user.username
        target_user.delete()
        messages.success(request, f'🗑️ User "{name}" deleted.')
    return redirect('admin_dashboard')


# ──────────────────────────────────────────────
# ADMIN CRUD: PASSES
# ──────────────────────────────────────────────

@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_edit_pass_view(request, pass_pk):
    """Admin: edit pass status."""
    bus_pass = get_object_or_404(BusPass, pk=pass_pk)
    if request.method == 'POST':
        new_status = request.POST.get('status', bus_pass.status)
        if new_status in dict(BusPass.STATUS_CHOICES):
            bus_pass.status = new_status
            bus_pass.save(update_fields=['status'])
            messages.success(request, f'✅ Pass {bus_pass.pass_id_short} status changed to "{new_status}".')
        else:
            messages.error(request, 'Invalid status.')
    return redirect('admin_dashboard')


@auth_required
@user_passes_test(is_admin, login_url='dashboard')
def admin_delete_pass_view(request, pass_pk):
    """Admin: delete a pass."""
    if request.method == 'POST':
        bus_pass = get_object_or_404(BusPass, pk=pass_pk)
        short = bus_pass.pass_id_short
        bus_pass.delete()
        messages.success(request, f'🗑️ Pass {short} deleted.')
    return redirect('admin_dashboard')

