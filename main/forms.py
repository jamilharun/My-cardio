from django import forms

from django import forms

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
