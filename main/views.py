import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string 
from django.urls import reverse
from django.utils import timezone 
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from weasyprint import HTML
from .forms import (HealthRiskForm, ProfileUpdateForm, UserForm, AssignPatientForm, RoleUpdateForm, AppointmentForm, UserUpdateForm,
                    ConsultationForm, RecommendationForm, DoctorAppointmentForm)
from .ai_model import predict_health_risk, generate_explanation, generate_recommendations, generate_health_report, convert_form_data_to_model_format    
from .models import (RiskAssessmentResult, CustomUser, UserProfile, DoctorPatientAssignment, SystemAlert, Recommendation, Appointment,
                    RiskAlert, DataAccessLog, EncryptedFieldMixin, Notification, TermsAcceptance)
from .utils import sanitize_text
import plotly.graph_objects as go
import base64
import json
import csv
import io

# debugging tool
logger = logging.getLogger(__name__)

def home(request):
    return render(request, "home.html")

@login_required
def profile_view(request):
    return render(request, 'profile.html', {'user': request.user})
def register_user(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        role = "patient"
        
        # Check if terms were accepted
        terms_accepted = request.POST.get("terms", False)
        
        if not terms_accepted:
            messages.error(request, "You must accept the terms and conditions to register.")
            return redirect("register")
            
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect("register")

        # Create user
        user = CustomUser.objects.create_user(username=username, email=email, password=password, role=role)


        # THIS IS WHERE YOU ADD THE TERMS ACCEPTANCE CODE
        if terms_accepted:
            # Get client IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
                
            TermsAcceptance.objects.create(
                user=user,
                ip_address=ip
            )

        # Manually create UserProfile (in case signals fail)
        UserProfile.objects.get_or_create(user=user)
        
        # Auto-login user after registration
        login(request, user)
        messages.success(request, "Registration successful!")
        # Redirect based on role
        if role == "doctor":
            return redirect("doctor_dashboard")
        elif role == "admin":
            return redirect("admin_dashboard")
        else:
            return redirect("patient_dashboard") 

    return render(request, "register.html")

def user_login(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = authenticate(request, email=email, password=password)

        storage = messages.get_messages(request)
        for _ in storage:
            pass

        if user is not None:
            login(request, user)
            list(messages.get_messages(request))
            messages.success(request, "Login successful!")

            # ✅ Get role from authenticated user
            role = user.role

            print(role)
            # ✅ Redirect based on role
            if role == "doctor":
                return redirect("doctor_dashboard")
            elif role == "admin":
                return redirect("admin_dashboard")
            else:
                return redirect("patient_dashboard")  # Default fallback patient

        else:
            list(messages.get_messages(request))
            messages.error(request, "Invalid email or password.")

    return render(request, "login.html")

def user_logout(request):
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    """Display and edit user profile"""
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect("profile")

    else:
        
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
    }
    return render(request, "users/profile.html", context)

@login_required
def health_risk_assessment(request):
    risk_result = None
    explanation = None
    previous_results = None
    report = None
    recommendations = None
    newRiskLevel = None

    if request.user.is_authenticated:
        previous_results = RiskAssessmentResult.objects.filter(user=request.user).order_by("-created_at")

    if request.method == "POST":
        form = HealthRiskForm(request.POST)
        if form.is_valid():
            user_data = form.cleaned_data
            
            try:
                # Convert form data to model format
                model_data = convert_form_data_to_model_format(user_data)
                
                # Make prediction
                risk_result = predict_health_risk(model_data)
                
                # Calculate risk level based on probability
                if risk_result["risk_probability"] <= 0.45:
                    newRiskLevel = "Low"
                elif risk_result["risk_probability"] <= 0.70:
                    newRiskLevel = "Medium"
                else:
                    newRiskLevel = "High"

                # Generate explanation (with error handling)
                try:
                    explanation = generate_explanation(
                        newRiskLevel,
                        risk_result["risk_probability"],
                        user_data
                    )
                except Exception as e:
                    logger.error(f"Error generating explanation: {str(e)}")
                    explanation = (
                        f"Your risk level is {newRiskLevel} with a probability of "
                        f"{risk_result['risk_probability']}. This indicates a potential "
                        "cardiovascular risk. Consult a healthcare professional for more details."
                    )

                # Generate recommendations
                recommendations = generate_recommendations(user_data, newRiskLevel)
                
                # Save to database
                try:
                    RiskAssessmentResult.objects.create(
                        user=request.user,
                        age=user_data["age"],
                        gender=user_data["gender"],
                        height=user_data.get("height"),  # New field
                        weight=user_data.get("weight"),  # New field
                        blood_pressure=user_data["BP"],
                        cholesterol_level=int(user_data["cholesterol_level"]),
                        glucose_level=int(user_data["glucose_level"]),
                        smoke=int(user_data["smoke"]),  # New field
                        smoke_frequency=user_data.get("smoke_frequency", ""),
                        alco=int(user_data["alco"]),  # New field
                        alco_frequency=user_data.get("alco_frequency", ""),
                        active=int(user_data["active"]),  # New field
                        workout_frequency=user_data.get("workout_frequency", 0),
                        chestpain=int(user_data["chestpain"]),  # New field
                        restingrelectro=int(user_data["restingrelectro"]),  # New field
                        maxheartrate=int(user_data.get("maxheartrate", 0)),  # New field
                        exerciseangia=int(user_data["exerciseangia"]),  # New field
                        bmi=model_data.get("BMI"),
                        risk_level=newRiskLevel,
                        risk_probability=risk_result["risk_probability"],                        
                        explanation=explanation,
                        recommendations=", ".join(recommendations) if isinstance(recommendations, list) else recommendations
                    )

                    
                except Exception as e:
                    logger.error(f"Error saving assessment result: {str(e)}")
                    messages.error(request, "There was an error saving your assessment results.")
                
            except Exception as e:
                logger.error(f"Error in health risk assessment: {str(e)}")
                messages.error(request, "There was an error processing your assessment. Please try again.")
                risk_result = {
                    "risk_level": "Error",
                    "risk_probability": 0.5,
                    "risk_score": 50,
                    "error": str(e)
                }
    else:
        form = HealthRiskForm()

    return render(request, "health_risk.html", {
        "form": form, 
        "risk_result": risk_result, 
        "explanation": explanation,
        "previous_results": previous_results,
        "report": report,
        "recommendations": recommendations,
        "newRiskLevel": newRiskLevel
    })

@login_required
def health_risk_history(request):
    # Fetch all risk assessments for the logged-in user, ordered by most recent
    risk_history = RiskAssessmentResult.objects.filter(user=request.user).order_by("-created_at")
    
    return render(request, "health_risk_history.html", {
        "risk_history": risk_history
    })

def export_report_pdf(request, report_id):
    # Get the current report and all previous reports for this user
    current_report = RiskAssessmentResult.objects.get(id=report_id)
    user_reports = RiskAssessmentResult.objects.filter(
        user=current_report.user
    ).order_by('-created_at')[:5]
    
    # Prepare data for the chart
    dates = [report.created_at.strftime("%b %d, %Y %H:%M") for report in user_reports]
    bp_values = [report.blood_pressure for report in user_reports]
    maxhr_values = [report.maxheartrate for report in user_reports]
    

    print("dates:",dates)
    print("bp_values:",bp_values)
    print("cholesterol_values:",maxhr_values)

    # Create the figure with actual historical data
    fig = go.Figure()
    
    # Blood Pressure trace
    fig.add_trace(go.Scatter(
        x=dates,
        y=bp_values,
        name='Blood Pressure (mmHg)',
        line=dict(color='#FF0000', width=2),
    ))
    
    # Cholesterol trace
    fig.add_trace(go.Scatter(
        x=dates,
        y=maxhr_values,
        name='Max blood rate',
        line=dict(color='#0000FF', width=2),
    ))

    # Save the chart as a static image
    buf = BytesIO()
    fig.write_image(buf, format="png", width=1000, height=600)
    chart_image = base64.b64encode(buf.getvalue()).decode("utf-8")
    
    # Prepare recommendations
    recommendations = current_report.recommendations.split(", ") if current_report.recommendations else []
    
    # Context data for template
    context = {
        "report": current_report,
        "chart_image": chart_image,
        "recommendations": recommendations,
    }
    
    # Render and return PDF
    html_string = render_to_string("report_pdf_template.html", context)
    pdf = HTML(string=html_string).write_pdf()
    
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=health_report_{report_id}.pdf"
    return response

# Ensure only admins can access this page
def admin_required(user):
    return user.is_authenticated and user.role == "admin"

@login_required
@user_passes_test(admin_required)
def manage_users(request):
    """Admin Dashboard - Manage Users"""

    # 📌 Get search query & filter parameters
    search_query = request.GET.get("search", "").strip()
    role_filter = request.GET.get("role", "")

    # 📌 Fetch users and apply search & filter conditions
    users = CustomUser.objects.all()

    if search_query:
        users = users.filter(
            username__icontains=search_query
        ) | users.filter(
            email__icontains=search_query
        )

    if role_filter:
        users = users.filter(role=role_filter)
    return render(request, "admin/manage_users.html", {
        "users": users,
        "search_query": search_query,
        "role_filter": role_filter,
    })

@login_required
@user_passes_test(admin_required)
def add_user(request):
    """Admin - Add New User"""
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])  # ✅ Encrypt password
            user.save()
            messages.success(request, "User added successfully!")
            return redirect("manage_users")
    else:
        form = UserForm()
    
    return render(request, "admin/add_user.html", {"form": form})

@login_required
@user_passes_test(admin_required)
def edit_user(request, user_id):
    """Admin - Edit Existing User"""
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == "POST":
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            messages.success(request, "User updated successfully!")
            return redirect("manage_users")
    else:
        form = UserForm(instance=user)
    
    return render(request, "admin/edit_user.html", {"form": form, "user": user})

@login_required
@user_passes_test(admin_required)
def delete_user(request, user_id):
    """Admin - Delete User"""
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == "POST":
        user.delete()
        messages.success(request, "User deleted successfully!")
        return redirect("manage_users")
    
    return render(request, "admin/delete_user.html", {"user": user})

@login_required
@user_passes_test(admin_required)
def admin_dashboard(request):
    total_users = CustomUser.objects.count()
    total_patients = CustomUser.objects.filter(role="patient").count()
    total_doctors = CustomUser.objects.filter(role="doctor").count()
    total_assessments = RiskAssessmentResult.objects.count()
    high_risk_cases = RiskAssessmentResult.objects.filter(risk_level="High").count()
    medium_risk_cases = RiskAssessmentResult.objects.filter(risk_level="Medium").count()
    low_risk_cases = RiskAssessmentResult.objects.filter(risk_level="Low").count()
    latest_assessments = RiskAssessmentResult.objects.order_by("-created_at")[:5]

    return render(request, "admin_dashboard.html", {
        "total_users": total_users,
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "total_assessments": total_assessments,
        "high_risk_cases": high_risk_cases,
        "medium_risk_cases": medium_risk_cases,
        "low_risk_cases": low_risk_cases,
        "latest_assessments": latest_assessments,
    })


# ✅ Ensure only Doctors can access this page
def doctor_required(user):
    return user.is_authenticated and user.role == "doctor"

@login_required
@user_passes_test(doctor_required)
def doctor_dashboard(request):
    """Doctor Dashboard Overview"""
    appointments = Appointment.objects.filter(doctor=request.user).order_by("-date")

    # Fetch patients assigned to the logged-in doctor
    assigned_patients = DoctorPatientAssignment.objects.filter(doctor=request.user).values_list("patient", flat=True)

     # Count total patients assigned to the doctor
    total_patients = CustomUser.objects.filter(id__in=assigned_patients, role="patient").count()

    # Fetch risk assessments for the assigned patients
    high_risk_patients = RiskAssessmentResult.objects.filter(
        user__in=assigned_patients, risk_level="High"
    ).count()
    low_risk_patients = RiskAssessmentResult.objects.filter(
        user__in=assigned_patients, risk_level="Low"
    ).count()
    medium_risk_patients = RiskAssessmentResult.objects.filter(
        user__in=assigned_patients, risk_level="Medium"
    ).count()

    risk_alerts = RiskAlert.objects.filter(doctor=request.user, is_read=False).order_by("-created_at")

    return render(request, "doctor_dashboard.html", {
        "total_patients": total_patients,
        "high_risk_patients": high_risk_patients,
        "low_risk_patients": low_risk_patients,
        "risk_alerts": risk_alerts,
        "appointments": appointments,
        "medium_risk_patients": medium_risk_patients
    })

@login_required
@user_passes_test(admin_required)
def manage_assignments(request):
    """Admin - Manage Doctor & Patient Assignments"""
    assignments = DoctorPatientAssignment.objects.all()
    return render(request, "admin/manage_assignments.html", {"assignments": assignments})

@login_required
@user_passes_test(admin_required)
def assign_patient(request):
    """Admin - Assign Patient to Doctor"""
    if request.method == "POST":
        form = AssignPatientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Patient assigned successfully!")
            return redirect("manage_assignments")
    else:
        form = AssignPatientForm()

    return render(request, "admin/assign_patient.html", {"form": form})

@login_required
@user_passes_test(admin_required)
def unassign_patient(request, assignment_id):
    """Admin - Remove a Patient from a Doctor"""
    assignment = get_object_or_404(DoctorPatientAssignment, id=assignment_id)
    if request.method == "POST":
        assignment.delete()
        messages.success(request, "Assignment removed successfully!")
        return redirect("manage_assignments")

    return render(request, "admin/unassign_patient.html", {"assignment": assignment})

@login_required
@user_passes_test(admin_required)
def system_analytics(request):
    """Admin - System Analytics Overview"""

    # ✅ Fetch Key Statistics
    total_users = CustomUser.objects.count()
    total_doctors = CustomUser.objects.filter(role="doctor").count()
    total_patients = CustomUser.objects.filter(role="patient").count()
    total_assessments = RiskAssessmentResult.objects.count()
    high_risk_cases = RiskAssessmentResult.objects.filter(risk_level="High").count()
    low_risk_cases = RiskAssessmentResult.objects.filter(risk_level="Low").count()
    Medium_risk_cases = RiskAssessmentResult.objects.filter(risk_level="Medium").count()

    # 📊 Data for Chart.js
    risk_trends = RiskAssessmentResult.objects.values("risk_level").order_by("created_at")  # Assuming created_at exists

    # Get all unique risk levels from database
    unique_risk_levels = RiskAssessmentResult.objects.values_list('risk_level', flat=True).distinct()

    # Initialize counts for all unique risk levels
    risk_counts = {level: 0 for level in unique_risk_levels}
    
    for assessment in risk_trends:
        risk_counts[assessment["risk_level"]] += 1

    risk_data_json = json.dumps(risk_counts)

    return render(request, "admin/system_analytics.html", {
        "total_users": total_users,
        "total_doctors": total_doctors,
        "total_patients": total_patients,
        "total_assessments": total_assessments,
        "high_risk_cases": high_risk_cases,
        "Medium_risk_cases": Medium_risk_cases,
        "low_risk_cases": low_risk_cases,
        "risk_data_json": risk_data_json,  # ✅ Send Chart.js data
    })

@login_required
@user_passes_test(admin_required)
def view_risk_assessments(request):
    """Admin - View All Risk Assessments"""

    # ✅ Filtering by risk level
    risk_level_filter = request.GET.get("risk_level")
    search_query = request.GET.get("search")

    assessments = RiskAssessmentResult.objects.all().order_by("-created_at")

    if risk_level_filter:
        assessments = assessments.filter(risk_level=risk_level_filter)

    if search_query:
        assessments = assessments.filter(user__username__icontains=search_query)

    return render(request, "admin/view_assessments.html", {
        "assessments": assessments,
        "risk_level_filter": risk_level_filter,
        "search_query": search_query,
    })

@login_required
@user_passes_test(admin_required)
def manage_roles(request):
    """Admin - Manage User Roles"""
    users = CustomUser.objects.all()
    return render(request, "admin/manage_roles.html", {"users": users})

@login_required
@user_passes_test(admin_required)
def update_user_role(request, user_id):
    """Admin - Update User Role"""
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        form = RoleUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "User role updated successfully!")
            return redirect("manage_roles")
    else:
        form = RoleUpdateForm(instance=user)

    return render(request, "admin/update_user_role.html", {"form": form, "user": user})

@login_required
@user_passes_test(admin_required)
def generate_reports(request):
    """Admin - Generate System Reports Page"""
    return render(request, "admin/generate_reports.html")

@login_required
@user_passes_test(admin_required)
def export_users_csv(request):
    """Export complete user data as CSV"""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="users_export_{timezone.now().date()}.csv"'

    writer = csv.writer(response)
    
    # Define all possible fields (including methods)
    field_names = [
        'id', 'username', 'email', 'role', 'get_role_display',
        'date_joined', 'last_login', 'is_active', 'is_staff', 
        'is_superuser'
    ]
    
    # Add any additional fields your CustomUser might have
    additional_fields = [
        'date_of_birth', 'gender', 'phone_number', 
        'address', 'city', 'country'
    ]
    
    # Create complete header row
    headers = []
    for field in field_names + additional_fields:
        if hasattr(CustomUser, field):
            # Format header names nicely
            header_name = field.replace('_', ' ').title()
            if field.startswith('get_'):
                header_name = header_name.replace('Get ', '').replace(' Display', '')
            headers.append(header_name)

    writer.writerow(headers)

    # Get all users
    users = CustomUser.objects.all().order_by('date_joined')
    
    for user in users:
        row = []
        for field in field_names + additional_fields:
            if hasattr(user, field):
                value = getattr(user, field)
                
                # Handle callable methods
                if callable(value):
                    value = value()
                
                # Format special field types
                if field == 'date_joined' or field == 'last_login':
                    value = value.strftime('%Y-%m-%d %H:%M') if value else ''
                elif field == 'date_of_birth' and value:
                    value = value.strftime('%Y-%m-%d')
                elif field == 'is_active' or field == 'is_staff' or field == 'is_superuser':
                    value = 'Yes' if value else 'No'
                
                row.append(str(value) if value is not None else '')
        
        writer.writerow(row)

    return response

@login_required
@user_passes_test(admin_required)
def export_risk_assessments_csv(request):
    """Export all Risk Assessment Data as CSV"""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="risk_assessments_report.csv"'

    writer = csv.writer(response)

    # **Column Headers**
    writer.writerow([
        "Patient", "Age", "Gender", "Blood Pressure", "Cholesterol Level",
        "Glucose Level", "BMI", "Risk Level", "Risk Probability",
        "Explanation", "Recommendations", "Smoke Frequency",
        "Alcohol Frequency", "Workout Frequency", "Date Created"
    ])

    # **Fetch all risk assessments**
    assessments = RiskAssessmentResult.objects.all()
    for assessment in assessments:
        writer.writerow([
            assessment.user.username if assessment.user else "Anonymous",
            assessment.age,
            assessment.gender,
            assessment.blood_pressure,
            # ✅ Convert 0/1/2 for BP, Cholesterol, and Glucose into human-readable text
            "Normal" if assessment.cholesterol_level == 0 else "Above Normal" if assessment.cholesterol_level == 1 else "Well Above Normal",
            "Normal" if assessment.glucose_level == 0 else "Above Normal" if assessment.glucose_level == 1 else "Well Above Normal",
            f"{assessment.bmi:.2f}" if assessment.bmi else "N/A",  # Format BMI with 2 decimal places
            assessment.risk_level,
            f"{assessment.risk_probability:.2%}",  # Converts to percentage (e.g., 0.15 → "15.00%")
            assessment.explanation or "N/A",
            assessment.recommendations or "N/A",
            assessment.smoke_frequency or "None",
            assessment.alco_frequency or "None",
            assessment.workout_frequency if assessment.workout_frequency is not None else "None",
            assessment.created_at.strftime("%Y-%m-%d %H:%M")  # Format date properly
        ])

    return response

@login_required
@user_passes_test(admin_required)
def export_users_pdf(request):
    """Export complete user data as a well-formatted PDF"""
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                          rightMargin=inch/2, leftMargin=inch/2,
                          topMargin=inch/2, bottomMargin=inch/2)
    
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("COMPREHENSIVE USER REPORT", styles['Title']))
    elements.append(Paragraph(f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 24))

    # Get all users
    users = CustomUser.objects.all().order_by('date_joined')

    # Define which fields to include (standard + any custom fields)
    field_config = [
        {'name': 'id', 'label': 'ID', 'width': 0.5*inch},
        {'name': 'username', 'label': 'Username', 'width': 1*inch},
        {'name': 'email', 'label': 'Email', 'width': 1.5*inch},
        {'name': 'get_role_display', 'label': 'Role', 'width': 0.8*inch},
        {'name': 'date_joined', 'label': 'Date Joined', 'width': 1*inch, 'format': '%Y-%m-%d %H:%M'},
        {'name': 'last_login', 'label': 'Last Login', 'width': 1*inch, 'format': '%Y-%m-%d %H:%M'},
        {'name': 'is_active', 'label': 'Active', 'width': 0.5*inch, 'format': lambda x: 'Yes' if x else 'No'},
        {'name': 'is_staff', 'label': 'Staff', 'width': 0.5*inch, 'format': lambda x: 'Yes' if x else 'No'},
        # Add any additional custom fields here
        {'name': 'date_of_birth', 'label': 'Birth Date', 'width': 0.8*inch, 'format': '%Y-%m-%d'},
        {'name': 'get_gender_display', 'label': 'Gender', 'width': 0.6*inch},
    ]

    # Filter to only include fields that exist on the model
    available_fields = [f for f in field_config if hasattr(CustomUser, f['name'])]
    
    # Prepare table data
    col_widths = [f['width'] for f in available_fields]
    headers = [f['label'] for f in available_fields]
    data = [headers]

    for user in users:
        row = []
        for field in available_fields:
            # Get the value
            value = getattr(user, field['name'])
            
            # Handle callable methods
            if callable(value):
                value = value()
            
            # Apply formatting if specified
            if 'format' in field:
                if callable(field['format']):
                    value = field['format'](value)
                elif value:
                    try:
                        value = value.strftime(field['format'])
                    except AttributeError:
                        pass
            
            row.append(str(value) if value is not None else 'N/A')
        data.append(row)

    # Create the table
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#D9E1F2')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Total Users: {users.count()}", styles['Normal']))

    # Build the PDF
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()

    # Create response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="users_report_{timezone.now().date()}.pdf"'
    response.write(pdf_data)
    return response

@login_required
@user_passes_test(admin_required)
def export_risk_assessments_pdf(request):
    """Export Risk Assessment Data as a well-formatted PDF"""
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="risk_assessments_report.pdf"'

    # ✅ Switch to Portrait Mode (More Readable)
    pdf = SimpleDocTemplate(response, pagesize=letter, leftMargin=0.5 * inch, rightMargin=0.5 * inch)
    elements = []  

    styles = getSampleStyleSheet()
    title = Paragraph("Risk Assessments Report", styles["Title"])
    elements.append(title)

    # ✅ Shorter Column Titles to Save Space
    data = [[
        "Patient", "Age", "BP", "Chol", "Glu", "BMI", "Risk", "Prob", "Date"
    ]]

    # ✅ Fetch Risk Assessment Data
    assessments = RiskAssessmentResult.objects.all()
    for assessment in assessments:
        data.append([
            assessment.user.username if assessment.user else "Anonymous",
            assessment.age,
            assessment.blood_pressure,
            "N" if assessment.cholesterol_level == 0 else "AN" if assessment.cholesterol_level == 1 else "WAN",
            "N" if assessment.glucose_level == 0 else "AN" if assessment.glucose_level == 1 else "WAN",
            f"{assessment.bmi:.1f}" if assessment.bmi else "N/A",
            assessment.risk_level[:4],  # Show only first 4 letters (e.g., "High")
            f"{assessment.risk_probability:.1%}",
            assessment.created_at.strftime("%Y-%m-%d")
        ])

    # ✅ Set Column Widths Dynamically
    col_widths = [
        1.2 * inch,  # Patient
        0.6 * inch,  # Age
        0.5 * inch,  # BP
        0.5 * inch,  # Chol
        0.5 * inch,  # Glu
        0.8 * inch,  # BMI
        0.8 * inch,  # Risk
        0.8 * inch,  # Prob
        1.2 * inch,  # Date
    ]

    # ✅ Table Styling
    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),  # ✅ Reduce Font Size
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    pdf.build(elements)

    return response

@login_required
@user_passes_test(admin_required)
def risk_trends(request):
    """Admin - Risk Trends Over Time"""

    # 📊 Aggregate risk levels per month
    risk_trend_data = (
        RiskAssessmentResult.objects.annotate(month=TruncMonth("created_at"))
        .values("month", "risk_level")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    # 📌 Convert data into JSON format for Chart.js
    trends = {}
    for entry in risk_trend_data:
        month = entry["month"].strftime("%Y-%m")  # Convert date to "YYYY-MM" format
        risk_level = entry["risk_level"]
        count = entry["count"]

        if month not in trends:
            trends[month] = {"High": 0, "Medium": 0, "Low": 0}
        trends[month][risk_level] = count

    risk_data_json = json.dumps(trends)  # ✅ Convert to JSON for frontend

    return render(request, "admin/risk_trends.html", {
        "risk_data_json": risk_data_json
    })

@login_required
@user_passes_test(admin_required)
def system_alerts(request):
    """Admin - View System Alerts"""
    alerts = SystemAlert.objects.order_by("-created_at")
    return render(request, "admin/system_alerts.html", {"alerts": alerts})

@login_required
@user_passes_test(admin_required)
def mark_alert_as_read_admin(request, alert_id):
    """Admin - Mark an Alert as Read"""
    alert = get_object_or_404(SystemAlert, id=alert_id)
    alert.is_read = True
    alert.save()
    messages.success(request, "Alert marked as read.")
    return redirect("system_alerts")

@login_required
@user_passes_test(admin_required)
def delete_alert(request, alert_id):
    """Admin - Delete an Alert"""
    alert = get_object_or_404(SystemAlert, id=alert_id)
    alert.delete()
    messages.success(request, "Alert deleted successfully.")
    return redirect("system_alerts")

@login_required
def patient_list(request):
    """Doctor - View & Search Assigned Patients"""
    
    if request.user.role != "doctor":
        return render(request, "error.html", {"message": "Access Denied: Only doctors can view assigned patients."})

    # Fetch all patients assigned to the logged-in doctor
    assignments = DoctorPatientAssignment.objects.filter(doctor=request.user)
    patients = [assignment.patient for assignment in assignments]

    # Get search parameters from request
    search_query = request.GET.get("search", "").strip()
    age_filter = request.GET.get("age", "").strip()
    risk_level_filter = request.GET.get("risk_level", "")
    
    # Dictionary to store latest assessment for each patient
    patient_assessments = {}
    filtered_patients = []
    
    # Process each patient
    for patient in patients:
        # Get the latest risk assessment for this patient
        assessment = RiskAssessmentResult.objects.filter(
            user=patient  # Using user instead of patient based on your code
        ).order_by("-created_at").first()
        
        # Store the assessment in our dictionary
        patient_assessments[patient.id] = assessment
        
        # Skip filtering if no filters are applied
        if not search_query and not age_filter and not risk_level_filter:
            filtered_patients.append(patient)
            continue
            
        # Name search filter
        if search_query and search_query.lower() not in patient.username.lower():
            continue
            
        # Skip age and risk level filters if patient has no assessment
        if (age_filter or risk_level_filter) and not assessment:
            continue
            
        # Age filter (if specified)
        if age_filter and assessment and str(assessment.age) != age_filter:
            continue
            
        # Risk level filter (if specified)
        if risk_level_filter and assessment and assessment.risk_level != risk_level_filter:
            continue
            
        # If we get here, the patient passed all applied filters
        filtered_patients.append(patient)

    return render(request, "doctor/patient_list.html", {
        "patients": filtered_patients,
        "search_query": search_query,
        "age_filter": age_filter,
        "risk_level_filter": risk_level_filter,
        "patient_assessments": patient_assessments,  # Pass the dictionary of assessments
    })

@login_required
def patient_detail(request, patient_id):
    """Doctor - View Individual Patient Record"""
    
    if request.user.role != "doctor":
        return render(request, "error.html", {"message": "Access Denied: Only doctors can view patient records."})

    # Fetch patient details & ensure they are assigned to this doctor
    patient = get_object_or_404(CustomUser, id=patient_id, role="patient")
    assignment = DoctorPatientAssignment.objects.filter(doctor=request.user, patient=patient).exists()

    if not assignment:
        return render(request, "error.html", {"message": "You are not assigned to this patient."})

    # Fetch patient's health history & past risk assessments
    risk_assessments = RiskAssessmentResult.objects.filter(user=patient).order_by("-created_at")

    return render(request, "doctor/patient_detail.html", {
        "patient": patient,
        "risk_assessments": risk_assessments,
    })

@login_required
def export_patient_csv(request, patient_id):
    """Doctor - Export Patient Report as CSV"""
    patient = get_object_or_404(CustomUser, id=patient_id, role="patient")

    # Ensure the doctor is assigned to this patient
    if not DoctorPatientAssignment.objects.filter(doctor=request.user, patient=patient).exists():
        return render(request, "error.html", {"message": "Access Denied: You are not assigned to this patient."})

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{patient.username}_health_report_{timezone.now().date()}.csv"'

    writer = csv.writer(response)
    
    # Patient Information Section
    writer.writerow(["PATIENT INFORMATION"])
    writer.writerow(["Name", patient.get_full_name() or patient.username])
    writer.writerow(["Email", patient.email])
    writer.writerow(["Gender", patient.get_gender_display() if hasattr(patient, 'get_gender_display') else "N/A"])
    writer.writerow([])  # Empty row

    # Risk Assessment Data Header
    headers = [
        "Assessment Date",
        "Risk Level", 
        "Risk Probability (%)",
        "Age",
        "Gender",
        "Blood Pressure (mmHg)",
        "Cholesterol Level",
        "Glucose Level",
        "BMI",
        "Smoker",
        "Smoking Frequency",
        "Alcohol Consumer",
        "Alcohol Frequency",
        "Physically Active",
        "Workout Frequency (times/week)",
        "Chest Pain",
        "Resting ECG Results",
        "Exercise-induced Angina",
        "Max Heart Rate",
        "Explanation",
        "Recommendations"
    ]
    writer.writerow(headers)

    # Risk Assessment Data Rows
    risk_assessments = RiskAssessmentResult.objects.filter(user=patient).order_by("-created_at")
    
    for assessment in risk_assessments:
        writer.writerow([
            assessment.created_at.strftime("%Y-%m-%d %H:%M"),
            assessment.risk_level,
            f"{assessment.risk_probability:.2%}",
            assessment.age,
            assessment.gender,
            assessment.blood_pressure,
            assessment.get_cholesterol_level_display() if hasattr(assessment, 'get_cholesterol_level_display') else assessment.cholesterol_level,
            assessment.get_glucose_level_display() if hasattr(assessment, 'get_glucose_level_display') else assessment.glucose_level,
            f"{assessment.bmi:.1f}" if assessment.bmi else "N/A",
            "Yes" if assessment.smoke else "No",
            assessment.get_smoke_frequency_display() if hasattr(assessment, 'get_smoke_frequency_display') else assessment.smoke_frequency,
            "Yes" if assessment.alco else "No",
            assessment.get_alco_frequency_display() if hasattr(assessment, 'get_alco_frequency_display') else assessment.alco_frequency,
            "Yes" if assessment.active else "No",
            assessment.workout_frequency,
            "Yes" if assessment.chestpain else "No",
            assessment.get_restingrelectro_display() if hasattr(assessment, 'get_restingrelectro_display') else assessment.restingrelectro,
            "Yes" if assessment.exerciseangia else "No",
            assessment.maxheartrate,
            assessment.explanation.replace('\n', ' ') if assessment.explanation else "N/A",
            assessment.recommendations.replace('\n', ' ') if assessment.recommendations else "N/A"
        ])

    return response

@login_required
def export_patient_pdf(request, patient_id):
    """Doctor - Export comprehensive patient report as PDF"""
    patient = get_object_or_404(CustomUser, id=patient_id, role="patient")

    # Verify doctor-patient assignment
    if not DoctorPatientAssignment.objects.filter(doctor=request.user, patient=patient).exists():
        return render(request, "error.html", {"message": "Access Denied: You are not assigned to this patient."})

    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                          rightMargin=inch/2, leftMargin=inch/2,
                          topMargin=inch/2, bottomMargin=inch/2)
    
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(f"COMPREHENSIVE PATIENT REPORT", styles['Title']))
    elements.append(Spacer(1, 24))

    # Patient Information Section
    patient_data = [
        ["Patient Name", patient.get_full_name() or patient.username],
        ["Email", patient.email],
        ["Date Joined", patient.date_joined.strftime("%Y-%m-%d")],
        ["Role", patient.get_role_display()],
    ]
    
    if hasattr(patient, 'date_of_birth') and patient.date_of_birth:
        patient_data.append(["Date of Birth", patient.date_of_birth.strftime("%Y-%m-%d")])
    if hasattr(patient, 'gender') and patient.gender:
        patient_data.append(["Gender", patient.get_gender_display()])

    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    
    elements.append(Paragraph("PATIENT INFORMATION", styles['Heading2']))
    elements.append(Spacer(1, 12))
    elements.append(patient_table)
    elements.append(Spacer(1, 24))

    # Risk Assessments Section
    elements.append(Paragraph("RISK ASSESSMENT HISTORY", styles['Heading2']))
    elements.append(Spacer(1, 12))

    risk_assessments = RiskAssessmentResult.objects.filter(user=patient).order_by("-created_at")
    
    for assessment in risk_assessments:
        # Assessment header
        elements.append(Paragraph(
            f"Assessment on {assessment.created_at.strftime('%Y-%m-%d %H:%M')}",
            styles['Heading3']
        ))
        
        # Risk summary
        risk_color = colors.red if assessment.risk_level == "High" else (
            colors.orange if assessment.risk_level == "Medium" else colors.green
        )
        
        risk_summary = [
            ["Risk Level", f"{assessment.risk_level}"],
            ["Risk Probability", f"{assessment.risk_probability:.2%}"],
            ["Age at Assessment", assessment.age],
            ["Blood Pressure", f"{assessment.blood_pressure} mmHg"],
            ["Cholesterol", "normal" if assessment.cholesterol_level == 0 else "above normal" if assessment.cholesterol_level == 1 else "well above normal"],
            ["Glucose", "normal" if assessment.glucose_level == 0 else "above normal" if assessment.glucose_level == 1 else "well above normal"],
            ["BMI", f"{assessment.bmi:.1f}" if assessment.bmi else "N/A"],
            ["Smoker", "Yes" if assessment.smoke else "No"],
            ["Exercise Frequency", f"{assessment.workout_frequency} times/week" if assessment.workout_frequency else "None"],
            ["Chest Pain", "Yes" if assessment.chestpain else "No"],
        ]
        
        # Create assessment table
        assessment_table = Table(risk_summary, colWidths=[2*inch, 4*inch])
        assessment_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('GRID', (0,0), (-1,-1), 1, colors.lightgrey),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ]))
        
        elements.append(assessment_table)
        elements.append(Spacer(1, 12))
        
        # Explanation and recommendations
        elements.append(Paragraph("Explanation:", styles['Heading4']))
        elements.append(Paragraph(assessment.explanation or "No explanation provided", styles['BodyText']))
        elements.append(Spacer(1, 12))
        
        if assessment.recommendations:
            elements.append(Paragraph("Recommendations:", styles['Heading4']))
            elements.append(Paragraph(assessment.recommendations, styles['BodyText']))
        
        elements.append(Spacer(1, 24))  # Extra space between assessments

    # Build the PDF
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()

    # Create response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{patient.username}_full_report.pdf"'
    response.write(pdf_data)
    return response


@login_required
def patient_detail(request, patient_id):
    """Doctor - View Individual Patient Record & Provide Recommendations"""
    
    if request.user.role != "doctor":
        return render(request, "error.html", {"message": "Access Denied: Only doctors can view patient records."})

    # Fetch patient details & ensure they are assigned to this doctor
    try:
        # Add debugging to see what's being looked for
        print(f"Looking for patient with ID: {patient_id}")
        
        # Check if role is case-sensitive
        patient = get_object_or_404(CustomUser, id=patient_id)
        print(f"Found patient: {patient.username}, Role: {patient.role}")
        
        # Make sure the role check isn't case sensitive 
        if patient.role.lower() != "patient":
            return render(request, "error.html", {"message": "Invalid patient record requested."})
            
        # Check assignment
        assignment = DoctorPatientAssignment.objects.filter(doctor=request.user, patient=patient).exists()
        
        if not assignment:
            return render(request, "error.html", {"message": "You are not assigned to this patient."})
            
        # Fetch patient's health history & past risk assessments
        risk_assessments = RiskAssessmentResult.objects.filter(user=patient).order_by("-created_at")
        recommendations = Recommendation.objects.filter(patient=patient, doctor=request.user).order_by("-created_at")
    
        # Handle recommendation submission
        if request.method == "POST":
            form = RecommendationForm(request.POST)
            if form.is_valid():
                recommendation = form.save(commit=False)
                recommendation.doctor = request.user
                recommendation.patient = patient
                
                # Get the latest assessment's associated risk assessment object
                latest_assessment = risk_assessments.first()
                if latest_assessment:
                    recommendation.risk_assessment = latest_assessment
                    
                recommendation.save()
                messages.success(request, "Recommendation added successfully!")
                return redirect("patient_detail", patient_id=patient.id)
        else:
            form = RecommendationForm()
    
        return render(request, "doctor/patient_detail.html", {
            "patient": patient,
            "risk_assessments": risk_assessments,
            "recommendations": recommendations,
            "form": form,
        })
        
    except Exception as e:
        print(f"Error in patient_detail: {str(e)}")
        return render(request, "error.html", {"message": f"Error loading patient details: {str(e)}"})


@login_required
def book_appointment(request, doctor_id):
    """Patient - Book an Appointment with a Doctor"""
    doctor = get_object_or_404(CustomUser, id=doctor_id, role="doctor")

    # Ensure the patient is assigned to this doctor
    if not DoctorPatientAssignment.objects.filter(doctor=doctor, patient=request.user).exists():
        return render(request, "error.html", {"message": "Access Denied: You are not assigned to this doctor."})

    if request.method == "POST":
        form = AppointmentForm(request.POST, is_admin=False)  # Use the form without doctor/patient fields
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.doctor = doctor
            appointment.patient = request.user
            appointment.status = "Pending"  # Default status for patient-created appointments
            appointment.save()
            messages.success(request, "Appointment request sent successfully!")
            return redirect("patient_dashboard")
    else:
        form = AppointmentForm(is_admin=False)  # Use the form without doctor/patient fields

    return render(request, "patient/book_appointment.html", {
        "form": form,
        "doctor": doctor
    })

@login_required
def doctor_appointments(request):
    """Doctor - View and Manage Appointments"""
    
    if request.user.role != "doctor":
        return render(request, "error.html", {"message": "Access Denied: Only doctors can manage appointments."})

    appointments = Appointment.objects.filter(doctor=request.user).order_by("-date", "-time")

    return render(request, "doctor/appointments.html", {"appointments": appointments})

@login_required
def doctor_create_appointment(request):
    if request.user.role != "doctor":
        return render(request, "error.html", {"message": "Access Denied: Only doctors can manage appointments."})
    
    if request.method == 'POST':
        form = DoctorAppointmentForm(request.POST, doctor=request.user)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.doctor = request.user
            appointment.status = 'Pending'
            appointment.save()
            messages.success(request, "Appointment created successfully!")
            return redirect('doctor_appointments')
    else:
        form = DoctorAppointmentForm(doctor=request.user)
    
    return render(request, 'doctor/create_appointment.html', {
        'form': form,
        'title': 'Create New Appointment'
    })

@login_required
def patient_appointments(request):
    """Patient - View and Manage Appointments"""
    
    if request.user.role != "patient":
        return render(request, "error.html", {"message": "Access Denied: Only patient can manage appointments."})

    appointments = Appointment.objects.filter(patient=request.user).order_by("-date", "-time")

    return render(request, "patient/appointments.html", {"appointments": appointments})

@login_required
def patient_appointment_detail(request, appointment_id):
    """Patient - View Detailed Information About an Appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    return render(request, "patient/appointment_detail.html", {"appointment": appointment})

@login_required
def update_appointment_status(request, appointment_id, status):
    """Doctor - Approve, Cancel, or Reschedule an Appointment"""
    
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
    appointment.status = status
    appointment.save()
    
    messages.success(request, f"Appointment {status.lower()} successfully!")
    return redirect("doctor_appointments")

@login_required
@user_passes_test(admin_required)  # Ensure only admins can access this view
def admin_create_appointment(request):
    """Admin - Create an Appointment for a Doctor and Patient"""
    if request.method == "POST":
        form = AppointmentForm(request.POST, is_admin=True)  # Use the form with doctor/patient fields
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.status = "Confirmed"  # Default status for admin-created appointments
            appointment.save()
            messages.success(request, "Appointment created successfully!")
            return redirect("admin_dashboard")  # Redirect to admin dashboard or another appropriate page
    else:
        form = AppointmentForm(is_admin=True)  # Use the form with doctor/patient fields

    return render(request, "admin/create_appointment.html", {"form": form})

@login_required
def risk_alerts(request):
    """Doctor - View Real-Time Risk Alerts"""
    
    if request.user.role != "doctor":
        return render(request, "error.html", {"message": "Access Denied: Only doctors can view risk alerts."})

    alerts = RiskAlert.objects.filter(doctor=request.user, is_read=False).order_by("-created_at")

    return render(request, "doctor/risk_alerts.html", {"alerts": alerts})

@login_required
def mark_alert_as_read(request, alert_id):
    """Doctor - Mark an Alert as Read"""

    print(f"Logged-in doctor: {request.user.username}")
    print(f"Attempting to mark alert {alert_id} as read.")

    alert = get_object_or_404(RiskAlert, id=alert_id, doctor=request.user)

    print(f"Alert found: {alert}")
    
    alert.is_read = True
    alert.save()

    print(f"Alert {alert_id} marked as read.")
    
    return redirect("risk_alerts")



@login_required
def patient_risk_chart(request, patient_id):
    """Doctor - View Patient Risk Trend as a Chart"""
    
    if request.user.role != "doctor":
        return render(request, "error.html", {"message": "Access Denied: Only doctors can view risk charts."})

    # Fetch patient details & risk assessments
    patient = get_object_or_404(CustomUser, id=patient_id, role="patient")
    risk_assessments = RiskAssessmentResult.objects.filter(user=patient).order_by("created_at")

    # Prepare data for Chart.js
    labels = [ra.created_at.strftime("%Y-%m-%d") for ra in risk_assessments]
    risk_levels = [ra.risk_level for ra in risk_assessments]

    # Convert risk levels to numerical values for graphing
    risk_mapping = {"Low": 1, "Medium": 2, "High": 3}
    risk_values = [risk_mapping.get(level, 0) for level in risk_levels]

    return render(request, "doctor/patient_risk_chart.html", {
        "patient": patient,
        "labels": json.dumps(labels),  # Convert to JSON for Chart.js
        "risk_values": json.dumps(risk_values),
    })


@login_required
def assessment_detail(request, assessment_id):
    """View details of a specific risk assessment"""
    
    assessment = get_object_or_404(RiskAssessmentResult, id=assessment_id)

    # Ensure only the patient or assigned doctor can view this
    if request.user != assessment.user and request.user.role != "doctor":
        return render(request, "error.html", {"message": "Access Denied: You are not authorized to view this assessment."})

    return render(request, "health/assessment_detail.html", {"assessment": assessment})


@login_required
def notifications_panel(request):
    """Doctor - View Notifications for High-Risk Patients"""
    
    if request.user.role != "doctor":
        return render(request, "error.html", {"message": "Access Denied: Only doctors can view notifications."})

    # Fetch only unread notifications
    notifications = RiskAlert.objects.filter(doctor=request.user, is_read=False).order_by("-created_at")

    return render(request, "doctor/notifications.html", {"notifications": notifications})

@login_required
def mark_notification_as_read(request, alert_id):
    """Doctor - Mark a Notification as Read"""
    
    notification = RiskAlert.objects.get(id=alert_id, doctor=request.user)
    notification.is_read = True
    notification.save()

    return redirect("notifications_panel")




# patient

@login_required
def patient_dashboard(request):
    """Patient - View Dashboard"""
    
    if request.user.role != "patient":
        return render(request, "error.html", {"message": "Access Denied: Only patients can access this page."})

    # Fetch upcoming appointments
    appointments = Appointment.objects.filter(patient=request.user).order_by("-date", "-time")

    # Fetch unread notifications
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by("-created_at")

    # Fetch past risk assessments
    risk_assessments = RiskAssessmentResult.objects.filter(user=request.user).order_by("-created_at")

    # Extract health data for visualization
    labels = [ra.created_at.strftime("%Y-%m-%d") for ra in risk_assessments]
    blood_pressure = [ra.blood_pressure for ra in risk_assessments]
    cholesterol = [ra.cholesterol_level for ra in risk_assessments]
    glucose = [ra.glucose_level for ra in risk_assessments]
    bmi = [ra.bmi for ra in risk_assessments]

    # Fetch recommendations from doctors
    recommendations = Recommendation.objects.filter(patient=request.user).order_by("-created_at")

    return render(request, "patient_dashboard.html", {
        "appointments": appointments,
        "notifications": notifications,
        "risk_assessments": risk_assessments,
        "recommendations": recommendations,
        "labels": json.dumps(labels),
        "blood_pressure": json.dumps(blood_pressure),
        "cholesterol": json.dumps(cholesterol),
        "glucose": json.dumps(glucose),
        "bmi": json.dumps(bmi),
    })

@login_required
def doctor_consultation(request, appointment_id):
    """Doctor - Add Consultation Notes & Update Appointment Status"""
    
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)

    if request.method == "POST":
        form = ConsultationForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, "Consultation notes saved successfully!")
            return redirect("doctor_dashboard")  # Redirect to doctor's dashboard

    else:
        form = ConsultationForm(instance=appointment)

    return render(request, "doctor/consultation.html", {
        "form": form,
        "appointment": appointment
    })


@login_required
def patient_health_statistics(request):
    """Patient - View Health Statistics on a Separate Page"""
    
    if request.user.role != "patient":
        return render(request, "error.html", {"message": "Access Denied: Only patients can access this page."})

    # Fetch latest health statistics
    risk_assessments = RiskAssessmentResult.objects.filter(user=request.user).order_by("-created_at")

    # Extract health data for visualization
    labels = [ra.created_at.strftime("%Y-%m-%d") for ra in risk_assessments]
    blood_pressure = [ra.blood_pressure for ra in risk_assessments]
    cholesterol = [ra.cholesterol_level for ra in risk_assessments]
    glucose = [ra.glucose_level for ra in risk_assessments]
    bmi = [ra.bmi for ra in risk_assessments]

    return render(request, "patient/patient_health_statistics.html", {
        "labels": json.dumps(labels),
        "blood_pressure": json.dumps(blood_pressure),
        "cholesterol": json.dumps(cholesterol),
        "glucose": json.dumps(glucose),
        "bmi": json.dumps(bmi),
    })



def log_data_access(user, data_type, object_id, action="Viewed"):
    DataAccessLog.objects.create(user=user, data_type=data_type, object_id=object_id, action=action)


def notifications_view(request):
    """Show user notifications"""
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    return render(request, "notifications.html", {"notifications": notifications})


@login_required
def mark_notification_as_read_patient(request, notification_id):
    """Mark a notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "success"})
    return redirect("patient_appointments")


def quick_password_reset(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = CustomUser.objects.get(email=email)
            # Generate token and uid
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Create reset URL
            reset_url = f"/reset/{uid}/{token}/"
            
            return render(request, 'quick_reset_link.html', {'reset_url': reset_url})
        except CustomUser.DoesNotExist:
            messages.error(request, "No user with that email exists")
            return redirect('password_reset')
    
    return render(request, 'quick_password_reset.html')


def custom_password_reset_done(request):
    reset_link = request.session.get('dev_reset_link', None)  # ✅ Retrieve from session
    
    print(f"DEBUG: Reset Link in Session: {reset_link}")  # 🔍 Check if it exists

    return render(request, 'password_reset_done.html', {'dev_reset_link': reset_link})



class SimplePasswordResetView(PasswordResetView):
    def form_valid(self, form):
        response = super().form_valid(form)  # ✅ Call parent class first

        if settings.DEBUG:
            email = form.cleaned_data['email']
            users = form.get_users(email)  # ✅ Correct way to get users
            user = next(users, None)  # ✅ Get the first user from the generator

            if user:
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                reset_link = self.request.build_absolute_uri(
                    reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                )

                # ✅ Store in session
                self.request.session['dev_reset_link'] = reset_link
                self.request.session.modified = True  # ✅ Force session update

                print(f"DEBUG: Stored Reset Link: {reset_link}")  # 🔍 Debugging Output

        return response  # ✅ Return the response at the end

@login_required
def patient_detail_assessment(request, assessment_id):
    # Verify the user is a doctor
    if not request.user.role == 'doctor':
        return JsonResponse({'error': 'Unauthorized access'}, status=403)
    
    # Get the assessment
    assessment = get_object_or_404(RiskAssessmentResult, id=assessment_id)
    
    # Verify the doctor is assigned to this patient
    is_assigned = DoctorPatientAssignment.objects.filter(
        doctor=request.user,
        patient=assessment.user
    ).exists()
    
    if not is_assigned:
        return JsonResponse({'error': 'You are not assigned to this patient'}, status=403)
    
    # Get all assessments for this patient (sorted by most recent first)
    all_assessments = RiskAssessmentResult.objects.filter(
        user=assessment.user
    ).order_by('-created_at')
    
    context = {
        'assessment': assessment,
        'patient': assessment.user,
        'all_assessments': all_assessments,
    }
    
    return render(request, 'doctor/patient_assessment_detail.html', context)


    # In your views.py
def terms_view(request):
    return render(request, 'terms.html')

def policy_view(request):
    return render(request, 'policy.html')