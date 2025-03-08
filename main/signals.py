from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import CustomUser, HealthHistory


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
