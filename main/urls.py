from django.urls import path
from .views import home, user_login, user_logout, register_user, dashboard, health_risk_assessment, health_risk_history

urlpatterns = [
    path('', home, name='home'),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("register/", register_user, name="register"),
    path("dashboard/", dashboard, name="dashboard"),
    path("health-risk/", health_risk_assessment, name="health_risk"),
    path("health-risk-history/", health_risk_history, name="health_risk_history"),
]