from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required  # ✅ FIXED: Import added!
from .models import CustomUser  # ✅ Import your CustomUser model
from .models import UserProfile
from .forms import ProfileUpdateForm

def home(request):
    return render(request, "home.html")

def register_user(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        role = request.POST["role"]  # Patient, Doctor, Admin

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect("register")

        user = CustomUser.objects.create_user(username=username, email=email, password=password, role=role)

        login(request, user)
        messages.success(request, "Registration successful!")
        return redirect("dashboard")

    return render(request, "register.html")

def user_login(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "login.html")

def user_logout(request):
    logout(request)
    return redirect("login")

@login_required
def dashboard(request):
    return render(request, "dashboard.html")

@login_required
def profile_view(request):
    try:
        profile = request.user.profile  # ✅ Try fetching the profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)  # ✅ Create profile if missing
        messages.warning(request, "Profile was missing, so we created one for you!")

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated!")
            return redirect("profile")
    else:
        form = ProfileUpdateForm(instance=profile)

    return render(request, "profile.html", {"profile": profile, "form": form})