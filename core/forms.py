from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile, BusPass, BoardingPoint
import re


class StudentRegistrationForm(UserCreationForm):
    first_name  = forms.CharField(max_length=50, required=True,  label='First Name')
    last_name   = forms.CharField(max_length=50, required=True,  label='Last Name')
    vml_no      = forms.CharField(max_length=20, required=True, label='USERNAME',
                                  help_text='Format: VML23CS200')
    phone       = forms.CharField(max_length=15, required=False, label='Phone Number')
    department  = forms.CharField(max_length=100, required=True, label='Department *')
    role        = forms.ChoiceField(choices=[('student', 'Student'), ('faculty', 'Faculty')],
                                    label='Role', initial='student')

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
            raise forms.ValidationError('USERNAME is required.')
        if not re.match(r'^VML\d{2}[A-Z]{2}\d{3}$', vml_no, re.IGNORECASE):
            raise forms.ValidationError(
                'USERNAME must be in format VML23CS200 (VML + 2 digits + 2 letters + 3 digits)'
            )
        vml_upper = vml_no.upper()
        # Check if already registered as a username
        if User.objects.filter(username=vml_upper).exists():
            raise forms.ValidationError('This USERNAME is already registered.')
        if UserProfile.objects.filter(vml_no__iexact=vml_upper).exists():
            raise forms.ValidationError('This USERNAME is already registered.')
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
            # Case-insensitive match: fetch all BoardingPoints whose name (uppercased) is in stops
            qs = BoardingPoint.objects.filter(
                name__in=stops
            ).order_by('fare', 'name')
            # Fall back to all points if none matched (route stops not in fare table yet)
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

