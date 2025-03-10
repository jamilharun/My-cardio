from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import logout, authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import HealthRiskForm
from .ai_model import predict_health_risk, generate_explanation, generate_recommendations, generate_health_report
from .models import RiskAssessmentResult
import plotly.graph_objects as go
import base64
from io import BytesIO

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
    previous_results = None
    report = None
    recommendations = None

    if request.user.is_authenticated:
        # Fetch previous results for the logged-in user
        previous_results = RiskAssessmentResult.objects.filter(user=request.user).order_by("-created_at")

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
            
             # Generate personalized recommendations
            recommendations = generate_recommendations(user_data, risk_result["risk_level"])

            # Generate personalized health report
            report = generate_health_report(user_data, risk_result)

            # Save the results to the database
            RiskAssessmentResult.objects.create(
                user=request.user if request.user.is_authenticated else None,  # Link to the logged-in user (optional)
                age=user_data["age"],
                gender="Male" if user_data["gender"] == 1 else "Female",
                blood_pressure=user_data["BP"],
                cholesterol_level=user_data["cholesterol_level"],
                glucose_level=user_data["glucose_level"],
                risk_level=risk_result["risk_level"],
                risk_probability=risk_result["risk_probability"],
                explanation=explanation,
                recommendations=", ".join(recommendations)
            )

    else:
        form = HealthRiskForm()

    return render(request, "health_risk.html", {
        "form": form, 
        "risk_result": risk_result, 
        "explanation": explanation,
        "previous_results": previous_results,
        "report": report,
        "recommendations": recommendations
    })

@login_required
def health_risk_history(request):
    # Fetch all risk assessments for the logged-in user, ordered by most recent
    risk_history = RiskAssessmentResult.objects.filter(user=request.user).order_by("-created_at")
    
    return render(request, "health_risk_history.html", {
        "risk_history": risk_history
    })


def export_report_pdf(request, report_id):
    # Fetch the report from the database
    report = RiskAssessmentResult.objects.get(id=report_id)

    # Generate a static chart using Plotly
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=['January', 'February', 'March', 'April', 'May', 'June', 'July'],  # Example data
        y=[120, 125, 130, 128, 132, 135, 140],  # Example data
        name='Blood Pressure'
    ))
    fig.update_layout(title="Health Metrics Over Time", xaxis_title="Date", yaxis_title="Value")
    
    # Save the chart as a static image
    buf = BytesIO()
    fig.write_image(buf, format="png")
    chart_image = base64.b64encode(buf.getvalue()).decode("utf-8")
    
    
    # Render the report as HTML
    html_string = render_to_string("report_pdf_template.html", {
        "report": report, 
        "chart_image": chart_image
    })
    
    # Convert HTML to PDF
    pdf = HTML(string=html_string).write_pdf()
    
    # Return the PDF as a response
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=health_report_{report_id}.pdf"
    return response