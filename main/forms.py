from django import forms
from .models import (UserProfile, CustomUser, DoctorPatientAssignment)

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["profile_picture", "bio", "phone_number", "address"]


class HealthRiskForm(forms.Form):
    age = forms.IntegerField(label="Age", min_value=1)
    gender = forms.ChoiceField(choices=[("Male", "Male"), ("Female", "Female")], label="Gender")
    BP = forms.IntegerField(label="Blood Pressure (Systolic)")
    cholesterol_level = forms.ChoiceField(choices=[(0, "Normal"), (1, "Above Normal"), (2, "Well Above Normal")], label="Cholesterol Level")
    glucose_level = forms.ChoiceField(choices=[(0, "Normal"), (1, "Above Normal"), (2, "Well Above Normal")], label="Glucose Level")
    smoke = forms.ChoiceField(choices=[(0, "No"), (1, "Yes")], label="Do you smoke?")
    alco = forms.ChoiceField(choices=[(0, "No"), (1, "Yes")], label="Do you consume alcohol?")
    active = forms.ChoiceField(choices=[(0, "No"), (1, "Yes")], label="Are you physically active?")
    chestpain = forms.ChoiceField(choices=[(0, "No"), (1, "Yes")], label="Do you experience chest pain?")
    restingrelectro = forms.ChoiceField(choices=[(0, "Normal"), (1, "ST-T wave abnormality"), (2, "Left ventricular hypertrophy")], label="Resting ECG results")
    maxheartrate = forms.IntegerField(label="Maximum Heart Rate Achieved")
    exerciseangia = forms.ChoiceField(choices=[(0, "No"), (1, "Yes")], label="Exercise-induced Angina?")

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