from django import forms
from .models import (UserProfile, CustomUser, DoctorPatientAssignment, Recommendation, Appointment)

class UserUpdateForm(forms.ModelForm):
    """Form for updating user basic details"""
    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "email"]

class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile"""

    phone_number = forms.CharField(
        max_length=15, required=False, label="Phone Number"
    )

    class Meta:
        model = UserProfile
        fields = ["profile_picture", "bio", "phone_number", "address", "date_of_birth", "gender", "emergency_contact"]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        """Decrypt encrypted fields when populating the form"""
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.phone_number:
            try:
                # Decrypt before displaying in the form
                self.fields["phone_number"].initial = self.instance.phone_number
            except Exception:
                pass  # In case of decryption failure, display raw value

    def clean_phone_number(self):
        """Ensure phone number gets encrypted before saving"""
        phone_number = self.cleaned_data.get("phone_number")
        return phone_number

class HealthRiskForm(forms.Form):
    age = forms.IntegerField(label="Age", min_value=1)
    gender = forms.ChoiceField(choices=[("Male", "Male"), ("Female", "Female")], label="Gender")
    height = forms.FloatField(help_text="Enter height in cm", label="Height (cm)") 
    weight = forms.FloatField(help_text="Enter weight in kg", label="Weight (kg)") 
    BP = forms.IntegerField(label="Blood Pressure (Systolic)")
    cholesterol_level = forms.ChoiceField(choices=[(0, "Normal"), (1, "Above Normal"), (2, "Well Above Normal")], label="Cholesterol Level")
    glucose_level = forms.ChoiceField(choices=[(0, "Normal"), (1, "Above Normal"), (2, "Well Above Normal")], label="Glucose Level")
    smoke = forms.ChoiceField(choices=[(0, "No"), (1, "Yes")], label="Do you smoke?")
    smoke_frequency = forms.ChoiceField(
        choices=[("often", "Often"), ("seldom", "Seldom"), ("occasional", "Occasional")],
        label="How often do you smoke?",
        required=False  # This field is only required if the user smokes
    )
    alco = forms.ChoiceField(choices=[(0, "No"), (1, "Yes")], label="Do you consume alcohol?")
    alco_frequency = forms.ChoiceField(
        choices=[("often", "Often"), ("seldom", "Seldom"), ("occasional", "Occasional")],
        label="How often do you consume alcohol?",
        required=False  # This field is only required if the user consumes alcohol
    )
    active = forms.ChoiceField(choices=[(0, "No"), (1, "Yes")], label="Are you physically active?")
    workout_frequency = forms.IntegerField(
        label="How many times a week do you work out? (0-20)",
        min_value=0,
        required=False  # This field is only required if the user is physically active
    )
    chestpain = forms.ChoiceField(choices=[(0, "No"), (1, "Yes")], label="Do you experience chest pain?")
    restingrelectro = forms.ChoiceField(choices=[(0, "Normal"), (1, "ST-T wave abnormality"), (2, "Left ventricular hypertrophy")], label="Resting ECG results")
    maxheartrate = forms.IntegerField(label="Maximum Heart Rate Achieved")
    exerciseangia = forms.ChoiceField(choices=[(0, "No"), (1, "Yes")], label="Exercise-induced Angina?")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["smoke_frequency"].widget.attrs["style"] = "display:none"
        self.fields["alco_frequency"].widget.attrs["style"] = "display:none"
        self.fields["workout_frequency"].widget.attrs["style"] = "display:none"


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False)  # ✅ Hide password input

    class Meta:
        model = CustomUser
        fields = ["username", "email", "role", "password"]

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data["password"]:  # ✅ Only update password if provided
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class AssignPatientForm(forms.ModelForm):
    doctor = forms.ModelChoiceField(queryset=CustomUser.objects.filter(role="doctor"), label="Select Doctor")
    patient = forms.ModelChoiceField(queryset=CustomUser.objects.filter(role="patient"), label="Select Patient")

    class Meta:
        model = DoctorPatientAssignment
        fields = ["doctor", "patient"]

class RoleUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["role"]

class RecommendationForm(forms.ModelForm):
    class Meta:
        model = Recommendation
        fields = ["recommendation_text"]
        widgets = {
            "recommendation_text": forms.Textarea(attrs={"rows": 4, "class": "border p-2 w-full rounded-lg"})
        }

class AppointmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.is_admin = kwargs.pop("is_admin", False)  # Check if the user is an admin
        super().__init__(*args, **kwargs)

        # Add doctor and patient fields for admins
        if self.is_admin:
            self.fields["doctor"] = forms.ModelChoiceField(
                queryset=CustomUser.objects.filter(role="doctor"),
                widget=forms.Select(attrs={"class": "border p-2 w-full rounded-lg"})
            )
            self.fields["patient"] = forms.ModelChoiceField(
                queryset=CustomUser.objects.filter(role="patient"),
                widget=forms.Select(attrs={"class": "border p-2 w-full rounded-lg"})
            )

    class Meta:
        model = Appointment
        fields = ["doctor", "patient", "date", "time", "consultation_notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "border p-2 w-full rounded-lg"}),
            "time": forms.TimeInput(attrs={"type": "time", "class": "border p-2 w-full rounded-lg"}),
            "consultation_notes": forms.Textarea(attrs={"class": "border p-2 w-full rounded-lg", "rows": 4}),
        }

class ConsultationForm(forms.ModelForm):
    """Form for doctors to update consultation notes and appointment status."""
    class Meta:
        model = Appointment
        fields = ["status", "consultation_notes"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "consultation_notes": forms.Textarea(attrs={"rows": 5, "class": "form-textarea"}),
        }