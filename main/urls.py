from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import home, user_login, user_logout, register_user, dashboard, health_risk_assessment, health_risk_history, export_report_pdf, profile_view

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
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)