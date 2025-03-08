from django.contrib import admin
from .models import CustomUser, UserProfile, HealthHistory


# from django.contrib.auth.models import Permission
# from django.contrib.contenttypes.models import ContentType

# Register your models here.

admin.site.register(CustomUser)
admin.site.register(UserProfile)
admin.site.register(HealthHistory)

# def assign_permissions(user):
#     """Assign default permissions based on role"""
#     if user.role == 'doctor':
#         # Allow doctors to view all health histories
#         content_type = ContentType.objects.get_for_model(HealthHistory)
#         permission = Permission.objects.get(content_type=content_type, codename='view_healthhistory')
#         user.user_permissions.add(permission)
#     elif user.role == 'admin':
#         user.is_staff = True
#         user.is_superuser = True  # Admins get full control
#         user.save()
