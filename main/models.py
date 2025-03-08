from django.contrib.auth.models import AbstractUser, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models

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


# Create your models here.

# User Roles Choices
USER_ROLES = (
    ('patient', 'Patient'),
    ('doctor', 'Doctor'),
    ('admin', 'Admin'),
)

class CustomUser(AbstractUser):
    """Custom User model extending Django's built-in user"""
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=USER_ROLES, default='patient')

    # Fix related_name conflicts
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="custom_user_set",  # Custom related_name to avoid conflicts
        blank=True,
        help_text="The groups this user belongs to."
    )

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_user_permissions_set",  # Custom related_name to avoid conflicts
        blank=True,
        help_text="Specific permissions for this user."
    )

    # Ensure authentication uses email instead of username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.username} ({self.role})"


class UserProfile(models.Model):
    """Additional health data for users"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="profile")
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    weight = models.FloatField(null=True, blank=True)  # in kg
    height = models.FloatField(null=True, blank=True)  # in cm
    medical_history = models.TextField(blank=True, help_text="Previous illnesses, medications, etc.")
    
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
