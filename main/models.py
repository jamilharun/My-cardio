from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.db import models
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

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.username

def user_profile_path(instance, filename):
    """Upload profile pictures to a specific user folder"""
    return f'profile_pics/{instance.user.id}/{filename}'

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    profile_picture = models.ImageField(upload_to=user_profile_path, default="profile_pics/default.jpg", blank=True)
    bio = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class HealthHistory(models.Model):
    """Stores user’s past health assessments"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="health_history")
    assessment_date = models.DateTimeField(auto_now_add=True)
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, help_text="AI-generated risk score")
    diagnosis = models.CharField(max_length=255, help_text="Health risk assessment result")
    recommendations = models.TextField(blank=True, help_text="Suggested preventive actions")
    
    def __str__(self):
        return f"{self.user.username} - {self.assessment_date} - {self.diagnosis}"

class RiskAssessmentResult(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)  # Link to the user (optional)
    age = models.IntegerField()
    gender = models.CharField(max_length=10)
    blood_pressure = models.IntegerField()
    cholesterol_level = models.IntegerField()
    glucose_level = models.IntegerField()
    risk_level = models.CharField(max_length=10)
    risk_probability = models.FloatField()
    explanation = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Risk Assessment for {self.user} on {self.created_at}"