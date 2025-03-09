from django.urls import path
from .views import home, user_login, user_logout, register_user, dashboard
from .views import profile_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', home, name='home'),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("register/", register_user, name="register"),
    path("dashboard/", dashboard, name="dashboard"),
    path("profile/", profile_view, name="profile"),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)