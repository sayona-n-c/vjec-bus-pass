from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import uuid


class Route(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    stops = models.JSONField(default=list, help_text="List of stop names in order")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_stops_list(self):
        if isinstance(self.stops, list):
            return self.stops
        return []


class Bus(models.Model):
    BUS_TYPE_CHOICES = [
        ('college', 'College Bus'),
        ('tourist', 'Tourist Bus'),
    ]

    bus_number = models.CharField(max_length=20, unique=True)
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True, related_name='buses')
    capacity = models.PositiveIntegerField(default=49)
    current_occupancy = models.PositiveIntegerField(default=0)
    bus_type = models.CharField(max_length=10, choices=BUS_TYPE_CHOICES, default='college')
    driver_name = models.CharField(max_length=100, blank=True)
    driver_phone = models.CharField(max_length=15, blank=True)
    driver = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_bus',
        help_text='Driver user account assigned to this bus'
    )
    is_active = models.BooleanField(default=True)
    # Live GPS fields (updated by driver)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    is_tracking = models.BooleanField(default=False, help_text='True while driver is sharing location')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['bus_number']

    def __str__(self):
        return f"Bus {self.bus_number} - {self.route}"

    @property
    def available_seats(self):
        return max(0, self.capacity - self.current_occupancy)

    @property
    def is_available(self):
        return self.available_seats > 0 and self.is_active

    @property
    def occupancy_percentage(self):
        if self.capacity == 0:
            return 0
        return int((self.current_occupancy / self.capacity) * 100)


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('driver', 'Driver'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    vml_no = models.CharField(
        max_length=20,
        unique=True,
        help_text="e.g. VML23CS200",
        blank=True,
        null=True
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=15, blank=True)
    department = models.CharField(max_length=100, blank=True)
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.vml_no or self.role})"

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username



# ────────────────────────────────────────────────────────
# BOARDING POINT FARE TABLE
# ────────────────────────────────────────────────────────
class BoardingPoint(models.Model):
    """Master table of boarding points with pre-calculated fares (rounded to nearest 10)."""
    name = models.CharField(max_length=200, unique=True)
    fare = models.PositiveIntegerField(
        default=0,
        help_text="Bus fare in INR – must be rounded to nearest 10 (e.g. 50, 60, 110)"
    )

    class Meta:
        ordering = ['fare', 'name']

    def __str__(self):
        return f"{self.name} (Rs.{self.fare})"

    @staticmethod
    def round_to_nearest_10(value: int) -> int:
        """Round a raw fare to the nearest 10 (standard arithmetic rounding)."""
        return round(int(value) / 10) * 10

    def clean(self):
        """Enforce minimum fare of ₹15 at the model/form-validation level."""
        if self.fare < 15:
            raise ValidationError({'fare': 'Fare must be at least ₹15. Zero-fare entries are not allowed.'})


class BusPass(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    pass_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bus_passes')
    bus = models.ForeignKey(Bus, on_delete=models.SET_NULL, null=True, related_name='passes')
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, related_name='passes')
    boarding_point = models.CharField(max_length=200)
    boarding_point_ref = models.ForeignKey(
        BoardingPoint, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bus_passes', help_text="Link to fare table entry"
    )
    amount_paid = models.PositiveIntegerField(
        default=0,
        help_text="Fare in INR rounded to nearest 10"
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True, default='',
                             help_text="Extra label, e.g. 'Faculty Reserve – Dr. John'")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Pass {self.pass_id_short} - {self.user.get_full_name()}"

    @property
    def pass_id_short(self) -> str:
        val: str = str(self.pass_id).upper()
        return val[:8]  # type: ignore[index]

    @property
    def pass_id_full(self):
        return str(self.pass_id).upper()


class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='attendances')
    bus_pass = models.ForeignKey(BusPass, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendances')
    scanned_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-scanned_at']

    def __str__(self):
        return f"{self.user.username} boarded Bus {self.bus.bus_number} at {self.scanned_at}"


class GPSLocation(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='gps_locations')
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    speed = models.FloatField(default=0.0, help_text="Speed in km/h")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        get_latest_by = 'timestamp'

    def __str__(self):
        return f"Bus {self.bus.bus_number} @ ({self.latitude}, {self.longitude})"


class BusCoordinator(models.Model):
    bus = models.OneToOneField(Bus, on_delete=models.CASCADE, related_name='coordinator')
    staff_id = models.CharField(max_length=20)
    name = models.CharField(max_length=150)
    department = models.CharField(max_length=100, blank=True)
    contact = models.CharField(max_length=15, blank=True)
    boarding_point = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.name} ({self.staff_id}) – Bus {self.bus.bus_number}"
