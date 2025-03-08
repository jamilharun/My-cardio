from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import CustomUser, HealthHistory
from django.contrib.auth import get_user_model


@receiver(post_save, sender=CustomUser)
def assign_permissions(sender, instance, created, **kwargs):
    """Assign default permissions based on role when a new user is created"""
    if created:  # Only assign when a user is created
        if instance.role == 'doctor':
            content_type = ContentType.objects.get_for_model(HealthHistory)
            permission = Permission.objects.get(content_type=content_type, codename='view_healthhistory')
            instance.user_permissions.add(permission)

        elif instance.role == 'admin':
            instance.is_staff = True
            instance.is_superuser = True  # Admins get full control
            instance.save()

CustomUser = get_user_model()

@receiver(post_migrate)
def create_default_users(sender, **kwargs):
    """Create default admin, doctor, and patient users after migration."""
    if sender.name == "main":  # Ensure it runs only for this app

        # Default users data
        default_users = [
            {"username": "admin_user", "email": "admin@example.com", "password": "Admin@123", "role": "admin"},
            {"username": "doctor_john", "email": "doctor@example.com", "password": "Doctor@123", "role": "doctor"},
            {"username": "patient_jane", "email": "patient@example.com", "password": "Patient@123", "role": "patient"},
        ]

        for user_data in default_users:
            if not CustomUser.objects.filter(email=user_data["email"]).exists():
                user = CustomUser.objects.create(
                    username=user_data["username"],
                    email=user_data["email"],
                    role=user_data["role"]  # Assign role separately
                )
                user.set_password(user_data["password"])  # Hash password
                user.save()  # Save the user after setting password

                print(f"✅ Created default {user.role}: {user.username}")