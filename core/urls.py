from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Routes & Buses
    path('routes/', views.routes_view, name='routes'),
    path('routes/<int:route_id>/buses/', views.bus_list_view, name='bus_list'),
    path('bus/<int:bus_id>/', views.bus_detail_view, name='bus_detail'),

    # Booking & Payment
    path('book/<int:bus_id>/', views.booking_view, name='booking'),
    path('payment/<uuid:pass_id>/', views.payment_view, name='payment'),
    path('payment/<uuid:pass_id>/confirm/', views.payment_confirm_view, name='payment_confirm'),
    path('pass/<uuid:pass_id>/', views.view_pass_view, name='view_pass'),
    path('my-passes/', views.my_passes_view, name='my_passes'),

    # QR Attendance
    path('qr/<int:bus_id>/', views.generate_qr_view, name='generate_qr'),
    path('api/scan-qr/', views.scan_qr_view, name='scan_qr'),

    # GPS / Map
    path('map/', views.map_view, name='map'),
    path('api/gps-update/', views.gps_update_view, name='gps_update'),
    path('api/bus-locations/', views.get_bus_locations_view, name='bus_locations'),

    # Admin Panel
    path('admin-panel/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-panel/edit-bus/<int:bus_id>/', views.admin_edit_bus_view, name='admin_edit_bus'),
    path('admin-panel/reset/<int:bus_id>/', views.admin_reset_occupancy_view, name='reset_occupancy'),
    path('admin-panel/bus-qr/<int:bus_id>/', views.bus_qr_view, name='bus_qr'),
    path('admin-panel/attendance/', views.admin_attendance_view, name='admin_attendance'),
    path('admin-panel/add-bus/', views.admin_add_bus_view, name='admin_add_bus'),
    path('admin-panel/delete-bus/<int:bus_id>/', views.admin_delete_bus_view, name='admin_delete_bus'),
    path('admin-panel/add-route/', views.admin_add_route_view, name='admin_add_route'),
    path('admin-panel/edit-route/<int:route_id>/', views.admin_edit_route_view, name='admin_edit_route'),
    path('admin-panel/delete-route/<int:route_id>/', views.admin_delete_route_view, name='admin_delete_route'),
    path('admin-panel/edit-user/<int:user_id>/', views.admin_edit_user_view, name='admin_edit_user'),
    path('admin-panel/delete-user/<int:user_id>/', views.admin_delete_user_view, name='admin_delete_user'),
    path('admin-panel/edit-pass/<int:pass_pk>/', views.admin_edit_pass_view, name='admin_edit_pass'),
    path('admin-panel/delete-pass/<int:pass_pk>/', views.admin_delete_pass_view, name='admin_delete_pass'),
    path('admin-panel/add-driver/', views.admin_add_driver_view, name='admin_add_driver'),

    # Physical Bus QR Scan → Mark Attendance
    path('mark-attendance/<int:bus_id>/', views.mark_attendance_view, name='mark_attendance'),

    # Student Camera QR Scanner for Attendance
    path('scan-attendance/', views.scan_attendance_view, name='scan_attendance'),

    # Driver GPS Interface
    path('driver/login/', views.driver_login_view, name='driver_login'),
    path('driver/dashboard/', views.driver_dashboard_view, name='driver_dashboard'),
    path('api/driver-gps/', views.driver_gps_push_view, name='driver_gps_push'),

    # AJAX: Boarding Points for a Bus
    path('api/boarding-points/<int:bus_id>/', views.api_boarding_points, name='api_boarding_points'),
]
