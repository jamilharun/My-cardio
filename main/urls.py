from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    home, user_login, user_logout, register_user, health_risk_assessment, health_risk_history,
    export_report_pdf, profile_view, admin_dashboard, doctor_dashboard, manage_users, add_user, edit_user, delete_user,
    manage_assignments, assign_patient, unassign_patient, system_analytics, view_risk_assessments, manage_roles,
    update_user_role, generate_reports, export_users_csv, export_risk_assessments_csv, export_users_pdf, export_risk_assessments_pdf,
    risk_trends, system_alerts, mark_alert_as_read, delete_alert, patient_list, patient_detail, export_patient_csv, export_patient_pdf,
    book_appointment,doctor_appointments, update_appointment_status, risk_alerts, mark_alert_as_read, patient_risk_chart, 
    assessment_detail, notifications_panel , mark_notification_as_read, patient_dashboard, doctor_consultation,
    patient_health_statistics,admin_create_appointment, patient_appointments, patient_appointment_detail, mark_notification_as_read_patient,
    quick_password_reset, custom_password_reset_done, SimplePasswordResetView, patient_detail_assessment, terms_view
)
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', home, name='home'),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("register/", register_user, name="register"),
    path("profile/", profile_view, name="profile"),
    path("health-risk/", health_risk_assessment, name="health_risk"),
    path("health-risk-history/", health_risk_history, name="health_risk_history"),
    path('terms/', terms_view, name='terms'),

    # im not sure if im gonna ass this
    # path("health-reports/", health_reports_view, name="health_reports"),

    path("export-report-pdf/<int:report_id>/", export_report_pdf, name="export_report_pdf"),
    path("assessment/<int:assessment_id>/", assessment_detail, name="assessment_detail"),
    path("consultation/<int:appointment_id>/", doctor_consultation, name="doctor_consultation"),
    path("doctor-dashboard/", doctor_dashboard, name="doctor_dashboard"),
    path("notifications/mark-as-read/<int:notification_id>/", mark_notification_as_read_patient, name="mark_notification_as_read_patient"),
    
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
    path("admin-dashboard/export-users-pdf/", export_users_pdf, name="export_users_pdf"),
    path("admin-dashboard/export-risk-assessments-csv/", export_risk_assessments_csv, name="export_risk_assessments_csv"),
    path("admin-dashboard/export-risk-assessments-pdf/", export_risk_assessments_pdf, name="export_risk_assessments_pdf"),
    path("admin-dashboard/risk-trends/", risk_trends, name="risk_trends"),
    path("admin-dashboard/system-alerts/", system_alerts, name="system_alerts"),
    path("admin-dashboard/mark-alert-as-read/<int:alert_id>/", mark_alert_as_read, name="mark_alert_as_read"),
    path("admin-dashboard/delete-alert/<int:alert_id>/", delete_alert, name="delete_alert"),
    path("admin-dashboard/create_appointment/", admin_create_appointment, name="create_appointment"),

    # doctors
    path("doctor-dashboard/patients/", patient_list, name="patient_list"),
    path("doctor-dashboard/patient/<int:patient_id>/", patient_detail, name="patient_detail"),
    path("doctor-dashboard/patient/<int:patient_id>/export-csv/", export_patient_csv, name="export_patient_csv"),
    path("doctor-dashboard/patient/<int:patient_id>/export-pdf/", export_patient_pdf, name="export_patient_pdf"),
    path("doctor-dashboard/patient/<int:patient_id>/risk-chart/", patient_risk_chart, name="patient_risk_chart"),
    path("doctor-dashboard/patient/assesment/<int:assessment_id>/", patient_detail_assessment, name="patient_detail_assessment"),
    path("doctor-dashboard/appointments/", doctor_appointments, name="doctor_appointments"),
    path("doctor-dashboard/update-appointment/<int:appointment_id>/<str:status>/", update_appointment_status, name="update_appointment_status"),
    path("doctor-dashboard/risk-alerts/", risk_alerts, name="risk_alerts"),
    path("doctor-dashboard/mark-alert-as-read/<int:alert_id>/", mark_alert_as_read, name="mark_alert_as_read"),
    path("doctor-dashboard/notifications/", notifications_panel, name="notifications_panel"),
    path("doctor-dashboard/mark-notification/<int:alert_id>/", mark_notification_as_read, name="mark_notification_as_read"),
    # path('doctor-dashboard/assignments/', doctor_assignments, name='doctor_assignments'),
    

    # patient
    path("patient-dashboard/", patient_dashboard, name="patient_dashboard"),
    path("patient/appointments/", patient_appointments, name="patient_appointments"),
    path("patient/appointments/<int:appointment_id>/", patient_appointment_detail, name="patient_appointment_detail"),
    path("patient/patient-health-statistics/", patient_health_statistics, name="patient_health_statistics"),

    # im not sure if im gonna add this or not
    path("patient/book-appointment/<int:doctor_id>/", book_appointment, name="book_appointment"), 


    # reset password
    path('password_reset/', SimplePasswordResetView.as_view(
        template_name='password_reset.html', 
        email_template_name='password_reset_email.html'),
        name='password_reset'),    # path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('password_reset/done/', custom_password_reset_done, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    path('quick_reset/', quick_password_reset, name='quick_reset'),
]
    

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)