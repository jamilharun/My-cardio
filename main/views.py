from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import logout, authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import HealthRiskForm
from .ai_model import predict_health_risk, generate_explanation

# Create your views here.
def home(request):
    return render(request, 'home.html')

def register_user(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        role = request.POST["role"]  # Patient, Doctor, Admin

        # Check if user already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect("register")

        # Create a new user
        user = CustomUser.objects.create(
            username=username,
            email=email,
            password=make_password(password),  # Hash password
            role=role
        )

        # Auto-login the user after registration
        login(request, user)
        messages.success(request, "Registration successful!")
        return redirect("dashboard")  # Redirect to dashboard after signup

    return render(request, "register.html")


def user_login(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect("dashboard")  # Redirect to a dashboard page
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "login.html")

def user_logout(request):
    logout(request)
    return redirect("login")

@login_required
def dashboard(request):
    return render(request, "dashboard.html")


def health_risk_assessment(request):
    risk_result = None
    explanation = None

    if request.method == "POST":
        form = HealthRiskForm(request.POST)
        if form.is_valid():
            # Get user input from the form
            user_data = form.cleaned_data
            
            # Convert gender to numeric format if needed
            user_data["gender"] = 1 if user_data["gender"].lower() == "male" else 0

            # Predict health risk using AI model
            risk_result = predict_health_risk(user_data)

            # Generate explanation using DeepSeek
            # if explination is undefined it should output something
            try:
                explanation = generate_explanation(
                    risk_result["risk_level"],
                    risk_result["risk_probability"],
                    user_data
                )
            except Exception as e:
                print(f"Error generating explanation: {e}")                
                explanation = "Unable to generate explanation due to an error."

    else:
        form = HealthRiskForm()

    return render(request, "health_risk.html", {"form": form, "risk_result": risk_result, "explanation": explanation})