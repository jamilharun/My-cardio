from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.utils.timezone import now
from django.db import models
from django.templatetags.static import static
from cryptography.fernet import Fernet
from django.conf import settings
from django.http import JsonResponse

# from django.contrib.auth import get_user_model

# ER Diagram Representation
# CustomUser
# ├── id (PK)
# ├── email (Unique, Used for Login)
# ├── username
# ├── password
# ├── role (Choices: Patient, Doctor, Admin)
# └── (Default Django user fields)

# UserProfile
# ├── id (PK)
# ├── user_id (FK → CustomUser)
# ├── age
# ├── gender
# ├── weight
# ├── height
# └── medical_history

# HealthHistory
# ├── id (PK)
# ├── user_id (FK → CustomUser)
# ├── assessment_date
# ├── risk_score
# ├── diagnosis
# └── recommendations

# User = get_user_model()

# Create your models here.

# User Roles Choices
class EncryptedFieldMixin(models.Field):
    """Mixin to encrypt and decrypt fields using Fernet encryption."""

    def get_internal_type(self):
        """Ensure Django treats this as a TextField."""
        return "TextField"

    def db_type(self, connection):
        """Define database type for compatibility."""
        return "text"  

    def from_db_value(self, value, expression, connection):
        """Decrypt when reading from the database"""
        if value is None:
            return None
            
        try:
            f = Fernet(settings.FERNET_SECRET_KEY.encode())
            return f.decrypt(value.encode()).decode()
        except Exception:
            return value

    def get_prep_value(self, value):
        """Encrypt before saving to the database"""
        if value is None:
            return None

        f = Fernet(settings.FERNET_SECRET_KEY.encode())
        return f.encrypt(value.encode()).decode()
    
    def to_python(self, value):
        """Ensure the field can handle decrypted values correctly."""
        if value is None:
            return None
        
        if isinstance(value, str):
            return value
        return self.from_db_value(value, None, None)

class EncryptedCharField(EncryptedFieldMixin, models.CharField):
    """Encrypted CharField using Fernet encryption."""
    def db_type(self, connection):
        return super().db_type(connection)

class EncryptedTextField(EncryptedFieldMixin, models.TextField):
    """Encrypted TextField using Fernet encryption."""
    def db_type(self, connection):
        return super().db_type(connection)

class EncryptedDecimalField(EncryptedFieldMixin, models.DecimalField):
    """Encrypted DecimalField using Fernet encryption."""
    def db_type(self, connection):
        return super().db_type(connection) 



class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, role="Patient"):
        if not email:
            raise ValueError("Users must have an email address")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, role=role)
        user.set_password(password)  # ✅ Encrypt password properly
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None):
        user = self.create_user(username, email, password)
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("Patient", "Patient"),
        ("Doctor", "Doctor"),
        ("Admin", "Admin"),
    ]
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    first_name = models.CharField(max_length=150, default="", blank=True)
    last_name = models.CharField(max_length=150, default="", blank=True)


    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(auto_now_add=True)  

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.username

def user_profile_path(instance, filename):
    """Upload profile pictures to a specific user folder"""
    return f'profile_pics/{instance.user.id}/{filename}'

class UserProfile(models.Model):
    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="profile"
    )
    profile_picture = models.ImageField(
        upload_to=user_profile_path, 
        default="profile_pics/default.jpg", 
        blank=True,
        null=True)

    bio = models.TextField(blank=True, null=True)
    phone_number = EncryptedCharField(max_length=15, blank=True, null=True)
    address = EncryptedCharField(max_length=255, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    emergency_contact = EncryptedCharField(max_length=15, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

    # def get_profile_picture_url(self):
    #     """Return profile picture URL or default static image."""
    #     if self.profile_picture:
    #         return self.profile_picture.url
    #     return static("assets/default.jpg")

class HealthHistory(models.Model):
    """Stores user’s past health assessments"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="health_history")
    assessment_date = models.DateTimeField(auto_now_add=True)
    risk_score = EncryptedDecimalField(max_digits=5, decimal_places=2, help_text="AI-generated risk score")
    diagnosis = EncryptedCharField(max_length=255, help_text="Health risk assessment result")
    recommendations = EncryptedTextField(blank=True, help_text="Suggested preventive actions")
    
    def __str__(self):
        return f"{self.user.username} - {self.assessment_date} - {self.diagnosis}"

class RiskAssessmentResult(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)  # Link to the user (optional)
    age = models.IntegerField()
    gender = models.CharField(max_length=10)
    blood_pressure = models.IntegerField()
    cholesterol_level = models.IntegerField()
    glucose_level = models.IntegerField()
    bmi = models.FloatField(null=True, blank=True)
    risk_level = models.CharField(max_length=10)
    risk_probability = models.FloatField()
    explanation = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Risk Assessment for {self.user} on {self.created_at}"


class DoctorPatientAssignment(models.Model):
    doctor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="assigned_patients")
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="assigned_doctor")
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.username} → {self.doctor.username}"

class SystemAlert(models.Model):
    ALERT_TYPES = [
        ("Security", "Security"),
        ("Update", "Update"),
        ("User", "User"),
        ("Risk", "Risk"),
    ]

    title = models.CharField(max_length=255)
    message = models.TextField()
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    created_at = models.DateTimeField(default=now)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.alert_type}: {self.title} ({'Read' if self.is_read else 'Unread'})"


# for doctors

class DoctorPatientAssignment(models.Model):
    doctor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="assigned_patients")
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="assigned_doctor")
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.username} → {self.doctor.username}"


class Recommendation(models.Model):
    doctor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="doctor_recommendations")
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="patient_recommendations")
    risk_assessment = models.ForeignKey(RiskAssessmentResult, on_delete=models.CASCADE, null=True, blank=True)
    recommendation_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recommendation by {self.doctor.username} for {self.patient.username}"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Confirmed", "Confirmed"),
        ("Cancelled", "Cancelled"),
    ]

    doctor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="doctor_appointments")
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="patient_appointments")
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(default=now)
    consultation_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Appointment on {self.date} at {self.time} - {self.status}"


class RiskAlert(models.Model):
    doctor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="risk_alerts")
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="patient_alerts")
    risk_assessment = models.ForeignKey(RiskAssessmentResult, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=now)
    is_read = models.BooleanField(default=False)  # Mark as read when viewed

    def __str__(self):
        return f"⚠ High Risk Alert - {self.patient.username} ({self.risk_assessment.risk_level})"

class HealthReport(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="health_reports")
    created_at = models.DateTimeField(default=now)
    risk_level = models.CharField(max_length=10, choices=[("Low", "Low"), ("Medium", "Medium"), ("High", "High")])
    risk_probability = models.FloatField(default=0)
    blood_pressure = models.IntegerField(default=0)
    cholesterol_level = models.FloatField(default=180)
    glucose_level = models.FloatField(default=0)
    bmi = models.FloatField(default=25)
    recommendations = models.TextField(default='')
    explanation = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Health Report for {self.user.username} on {self.created_at.strftime('%Y-%m-%d')}"





class DataAccessLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    accessed_at = models.DateTimeField(auto_now_add=True)
    data_type = models.CharField(max_length=255)  # e.g., "Health Report"
    object_id = models.IntegerField()
    action = models.CharField(max_length=50)  # e.g., "Viewed", "Edited"

    def __str__(self):
        return f"{self.user.username} accessed {self.data_type} (ID: {self.object_id}) on {self.accessed_at}"



class Notification(models.Model):
    """Stores notifications for users."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"

