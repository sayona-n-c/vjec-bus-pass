from django.contrib import admin
from .models import Route, Bus, UserProfile, BusPass, Attendance, GPSLocation, BusCoordinator, BoardingPoint

# ── Django Admin Branding ──────────────────────────────────────────
admin.site.site_header = "VJEC Bus Pass Admin"
admin.site.site_title  = "VJEC Bus Pass Admin"
admin.site.index_title = "Administration Panel"


@admin.register(BoardingPoint)
class BoardingPointAdmin(admin.ModelAdmin):
    list_display = ('name', 'fare')
    list_editable = ('fare',)            # ← admins can edit fare directly from the list page
    search_fields = ('name',)
    list_filter = ('fare',)
    ordering = ('fare', 'name')




@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'stops_count', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')

    def stops_count(self, obj):  # pyre-ignore[16]
        return len(obj.get_stops_list())
    stops_count.short_description = 'Stops'  # type: ignore[attr-defined]


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('bus_number', 'bus_type', 'route', 'capacity', 'current_occupancy', 'available_seats', 'is_active')
    list_filter = ('is_active', 'bus_type', 'route')
    search_fields = ('bus_number', 'driver_name')
    readonly_fields = ('available_seats', 'occupancy_percentage')

    def available_seats(self, obj):  # pyre-ignore[16]
        return obj.available_seats
    available_seats.short_description = 'Available Seats'  # type: ignore[attr-defined]


@admin.register(BusCoordinator)
class BusCoordinatorAdmin(admin.ModelAdmin):
    list_display = ('staff_id', 'name', 'department', 'contact', 'bus', 'boarding_point')
    search_fields = ('staff_id', 'name', 'bus__bus_number')
    list_filter = ('department',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'vml_no', 'role', 'department', 'phone', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'vml_no')


@admin.register(BusPass)
class BusPassAdmin(admin.ModelAdmin):
    list_display = ('pass_id_short', 'user', 'bus', 'route', 'boarding_point', 'amount_paid', 'status', 'created_at')
    list_filter = ('status', 'route')
    search_fields = ('user__username', 'user__first_name', 'boarding_point')
    readonly_fields = ('pass_id',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'bus', 'date', 'scanned_at')
    list_filter = ('date', 'bus')
    search_fields = ('user__username',)


@admin.register(GPSLocation)
class GPSLocationAdmin(admin.ModelAdmin):
    list_display = ('bus', 'latitude', 'longitude', 'speed', 'timestamp')
    list_filter = ('bus',)
