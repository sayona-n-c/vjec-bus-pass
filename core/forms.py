from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile, BusPass, BoardingPoint, Bus
import re


class StudentRegistrationForm(UserCreationForm):
    first_name   = forms.CharField(max_length=50, required=True,  label='First Name')
    last_name    = forms.CharField(max_length=50, required=True,  label='Last Name')
    vml_no       = forms.CharField(max_length=20, required=True, label='College ID',
                                   help_text='Student: VML23CS200  |  Faculty/Staff: SC1234 or FC1234')
    phone        = forms.CharField(max_length=15, required=False, label='Phone Number')
    department   = forms.CharField(max_length=100, required=True, label='Department')
    role         = forms.ChoiceField(
                       choices=[('student', 'Student'), ('faculty', 'Faculty / Staff')],
                       label='Role', initial='student')
    student_type = forms.ChoiceField(
                       choices=[('day_scholar', 'Day Scholar'), ('hosteler', 'Hosteler')],
                       label='Student Type', initial='hosteler',
                       required=False)

    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the inherited 'username' field — we use vml_no as username
        if 'username' in self.fields:
            del self.fields['username']

    def clean_vml_no(self):
        vml_no = self.cleaned_data.get('vml_no', '').strip()
        if not vml_no:
            raise forms.ValidationError('College ID is required.')
        vml_upper = vml_no.upper()
        # Student format: VML23CS200 (VML + 2 digits + 2 letters + 3 digits)
        student_ok = re.match(r'^VML\d{2}[A-Z]{2}\d{3}$', vml_upper)
        # Faculty/Staff format: SC1234 or FC1234 (2 letters + 4 digits)
        faculty_ok = re.match(r'^[A-Z]{2}\d{4}$', vml_upper)
        if not (student_ok or faculty_ok):
            raise forms.ValidationError(
                'Invalid ID. Student: VML23CS200  |  Faculty/Staff: SC1234 or FC1234'
            )
        # Check uniqueness
        if User.objects.filter(username=vml_upper).exists():
            raise forms.ValidationError('This ID is already registered.')
        if UserProfile.objects.filter(vml_no__iexact=vml_upper).exists():
            raise forms.ValidationError('This ID is already registered.')
        return vml_upper


class BusPassBookingForm(forms.Form):
    """Booking form – boarding_point is chosen from BoardingPoint fare table
    filtered to stops that actually appear on the selected bus route."""

    boarding_point = forms.ModelChoiceField(
        queryset=BoardingPoint.objects.none(),
        empty_label='-- Select Your Boarding Point --',
        label='Boarding Point',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_boarding_point'}),
        help_text='Fare is automatically calculated from the fare table.'
    )

    def __init__(self, *args, bus=None, **kwargs):
        super().__init__(*args, **kwargs)
        if bus and bus.route:
            stops = [s.strip().upper() for s in bus.route.get_stops_list()]
            qs = BoardingPoint.objects.filter(
                name__in=stops
            ).order_by('fare', 'name')
            if not qs.exists():
                qs = BoardingPoint.objects.all()
            self.fields['boarding_point'].queryset = qs
        else:
            self.fields['boarding_point'].queryset = BoardingPoint.objects.all()

    def get_fare(self) -> int:
        """Return the fare for the selected boarding point, rounded to nearest 10."""
        bp = self.cleaned_data.get('boarding_point')
        if bp:
            return BoardingPoint.round_to_nearest_10(bp.fare)
        return 0


class FacultyReserveForm(forms.Form):
    """Admin form for reserving a seat for a faculty/staff member (₹0 pass)."""

    faculty_name = forms.CharField(
        max_length=100,
        required=True,
        label='Faculty / Staff Name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Dr. Anitha Mathew'}),
    )
    bus = forms.ModelChoiceField(
        queryset=Bus.objects.filter(is_active=True).select_related('route').order_by('bus_number'),
        empty_label='-- Select Bus --',
        label='Bus',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    boarding_point = forms.ModelChoiceField(
        queryset=BoardingPoint.objects.all().order_by('fare', 'name'),
        empty_label='-- Select Boarding Point (optional) --',
        label='Boarding Point',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
