from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    home, user_login, user_logout, register_user, dashboard, health_risk_assessment, health_risk_history,
    export_report_pdf, profile_view, admin_dashboard, doctor_dashboard, manage_users, add_user, edit_user, delete_user,
    manage_assignments, assign_patient, unassign_patient, system_analytics, view_risk_assessments, manage_roles,
    update_user_role, generate_reports, export_users_csv, export_risk_assessments_csv, export_users_pdf, export_risk_assessments_pdf,
    risk_trends, system_alerts, mark_alert_as_read, delete_alert
)


urlpatterns = [
    path('', home, name='home'),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("register/", register_user, name="register"),
    path("dashboard/", dashboard, name="dashboard"),
    path("profile/", profile_view, name="profile"),
    path("health-risk/", health_risk_assessment, name="health_risk"),
    path("health-risk-history/", health_risk_history, name="health_risk_history"),
    path("export-report-pdf/<int:report_id>/", export_report_pdf, name="export_report_pdf"),

    path("doctor-dashboard/", doctor_dashboard, name="doctor_dashboard"),
    
    # dashboard roles admin
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/manage-users/", manage_users, name="manage_users"),
    path("admin-dashboard/add-user/", add_user, name="add_user"),
    path("admin-dashboard/edit-user/<int:user_id>/", edit_user, name="edit_user"),
    path("admin-dashboard/delete-user/<int:user_id>/", delete_user, name="delete_user"),
    path("admin-dashboard/manage-assignments/", manage_assignments, name="manage_assignments"),
    path("admin-dashboard/assign-patient/", assign_patient, name="assign_patient"),
    path("admin-dashboard/unassign-patient/<int:assignment_id>/", unassign_patient, name="unassign_patient"),
    path("admin-dashboard/system-analytics/", system_analytics, name="system_analytics"),
    path("admin-dashboard/view-assessments/", view_risk_assessments, name="view_assessments"),
    path("admin-dashboard/security-permissions/", manage_roles, name="manage_roles"),
    path("admin-dashboard/update-user-role/<int:user_id>/", update_user_role, name="update_user_role"),
    path("admin-dashboard/generate-reports/", generate_reports, name="generate_reports"),
    path("admin-dashboard/export-users-csv/", export_users_csv, name="export_users_csv"),
    path("admin-dashboard/export-risk-assessments-csv/", export_risk_assessments_csv, name="export_risk_assessments_csv"),
    path("admin-dashboard/export-users-pdf/", export_users_pdf, name="export_users_pdf"),
    path("admin-dashboard/export-risk-assessments-pdf/", export_risk_assessments_pdf, name="export_risk_assessments_pdf"),
    path("admin-dashboard/risk-trends/", risk_trends, name="risk_trends"),
    path("admin-dashboard/system-alerts/", system_alerts, name="system_alerts"),
    path("admin-dashboard/mark-alert-as-read/<int:alert_id>/", mark_alert_as_read, name="mark_alert_as_read"),
    path("admin-dashboard/delete-alert/<int:alert_id>/", delete_alert, name="delete_alert"),

]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)