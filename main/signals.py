from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from .models import UserProfile, CustomUser, HealthHistory, RiskAssessmentResult, SystemAlert, Appointment, DoctorPatientAssignment, Notification
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.conf import settings

CustomUser = get_user_model()

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

@receiver(post_save, sender=CustomUser)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_profile(sender, instance, **kwargs):
    """Ensure profile is saved when the user is updated"""
    if hasattr(instance, "profile"):  # ✅ Prevents errors if profile doesn't exist
        instance.profile.save()            

@receiver(post_save, sender=CustomUser)
def user_created_alert(sender, instance, created, **kwargs):
    """Create an alert when a new user registers"""
    if created:
        SystemAlert.objects.create(
            title="New User Registered",
            message=f"A new {instance.role} ({instance.username}) has registered.",
            alert_type="User"
        )

@receiver(post_save, sender=RiskAssessmentResult)
def high_risk_alert(sender, instance, created, **kwargs):
    """Create an alert when a high-risk assessment is made"""
    if created and instance.risk_level == "High":
        SystemAlert.objects.create(
            title="High-Risk Patient Alert",
            message=f"Patient {instance.user.username} has been classified as HIGH RISK.",
            alert_type="Risk"
        )

@receiver(post_save, sender=RiskAssessmentResult)
def create_risk_alert(sender, instance, created, **kwargs):
    """Automatically create an alert when a high-risk patient is identified"""
    print(f"Signal triggered for RiskAssessmentResult ID: {instance.id}, Created: {created}, Risk Level: {instance.risk_level}")

    if created and instance.risk_level == "High":
        # Find the assigned doctor
        assignment = DoctorPatientAssignment.objects.filter(patient=instance.user).first()
        if assignment:
            print(f"Assigned doctor: {assignment.doctor.username}")
            RiskAlert.objects.create(
                doctor=assignment.doctor,
                patient=instance.user,
                risk_assessment=instance
            )
            print("RiskAlert created successfully.")
        else:
            print("No doctor assigned to this patient.")


@receiver(post_save, sender=Appointment)
def notify_patient(sender, instance, created, **kwargs):
    """Send a notification when a doctor schedules an appointment for a patient."""
    if created:  # Only notify when the appointment is newly created
        message = f"You have a new appointment with Dr. {instance.doctor.username} on {instance.date} at {instance.time}."
        Notification.objects.create(user=instance.patient, message=message)