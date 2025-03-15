from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models.functions import TruncMonth
from django.db.models import Count

from .forms import (HealthRiskForm, ProfileUpdateForm, UserForm, AssignPatientForm, RoleUpdateForm, AppointmentForm, UserUpdateForm,
                    ConsultationForm)
from .ai_model import predict_health_risk, generate_explanation, generate_recommendations, generate_health_report
from .models import (RiskAssessmentResult, CustomUser, UserProfile, DoctorPatientAssignment, SystemAlert, Recommendation, Appointment,
                    RiskAlert, DataAccessLog, EncryptedFieldMixin, Notification)
import plotly.graph_objects as go
import base64
from io import BytesIO
from .utils import sanitize_text
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import csv
from django.core.exceptions import PermissionDenied

# debugging tool
import logging

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
        role = request.POST["role"]  # Patient, Doctor, Admin

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect("register")

        # ✅ Create user
        user = CustomUser.objects.create_user(username=username, email=email, password=password, role=role)

        # ✅ Manually create UserProfile (in case signals fail)
        UserProfile.objects.get_or_create(user=user)
        
        # ✅ Auto-login user after registration
        login(request, user)
        messages.success(request, "Registration successful!")
        # ✅ Redirect based on role
        if role == "Doctor":
            return redirect("doctor_dashboard")
        elif role == "Admin":
            return redirect("admin_dashboard")
        else:
            return redirect("patient_dashboard")  # Default fallback patient
            return redirect("patient_dashboard")  # Default fallback patient

    return render(request, "register.html")

def user_login(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
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
                return redirect("patient_dashboard")  # Default fallback patient

        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "login.html")

def user_logout(request):
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    """Display and edit user profile"""
    """Display and edit user profile"""
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect("profile")  # Redirect to profile page after saving

        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect("profile")  # Redirect to profile page after saving

    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
    }
    return render(request, "users/profile.html", context)
    context = {
        "user_form": user_form,
        "profile_form": profile_form,
    }
    return render(request, "users/profile.html", context)

@login_required
@login_required
def health_risk_assessment(request):
    risk_result = None
    explanation = None
    previous_results = None
    report = None
    recommendations = None
    # personalized_advice = None

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

            # ✅ Ensure both height and weight are valid before calculating BMI
            if user_data.get("height") and user_data.get("weight"):
                try:
                    height_m = float(user_data["height"]) / 100  # Convert cm to meters
                    weight_kg = float(user_data["weight"])
                    user_data["bmi"] = round(weight_kg / (height_m ** 2), 2)
                except (ValueError, TypeError, ZeroDivisionError) as e:
                    print(f"Error calculating BMI: {e}")  # Debugging statement
                    user_data["bmi"] = None  # Avoid crashes by setting BMI to None
            else:
                print("Missing height or weight, cannot calculate BMI.")  # Debugging statement
                user_data["bmi"] = None

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

            print(f"Generated Report: {report}") 

            explanation = generate_explanation(risk_result["risk_level"], risk_result["risk_probability"], user_data)
            sanitized_explanation = sanitize_text(explanation)

            try:
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
            except UnicodeEncodeError as e:
                logger.error(f"UnicodeEncodeError: {e}")
                logger.error(f"Problematic data: {explanation}")
                raise

    else:
        form = HealthRiskForm()

    return render(request, "health_risk.html", {
        "form": form, 
        "risk_result": risk_result, 
        "explanation": explanation,
        "previous_results": previous_results,
        "report": report,
        "recommendations": recommendations,
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
    low_risk_cases = RiskAssessmentResult.objects.filter(risk_level="Low").count()
    latest_assessments = RiskAssessmentResult.objects.order_by("-created_at")[:5]

    return render(request, "admin_dashboard.html", {
        "total_users": total_users,
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "total_assessments": total_assessments,
        "high_risk_cases": high_risk_cases,
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

    total_patients = CustomUser.objects.filter(role="patient").count()
    high_risk_patients = RiskAssessmentResult.objects.filter(risk_level="High").count()
    low_risk_patients = RiskAssessmentResult.objects.filter(risk_level="Low").count()

    risk_alerts = ["Patient John Doe has a high risk of cardiovascular disease!"]

    return render(request, "doctor_dashboard.html", {
        "total_patients": total_patients,
        "high_risk_patients": high_risk_patients,
        "low_risk_patients": low_risk_patients,
        "risk_alerts": risk_alerts,
        "appointments": appointments
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

    # 📊 Data for Chart.js
    risk_trends = RiskAssessmentResult.objects.values("risk_level").order_by("created_at")  # Assuming created_at exists
    risk_counts = {"High": 0, "Medium": 0, "Low": 0}
    
    for assessment in risk_trends:
        risk_counts[assessment["risk_level"]] += 1

    risk_data_json = json.dumps(risk_counts)

    return render(request, "admin/system_analytics.html", {
        "total_users": total_users,
        "total_doctors": total_doctors,
        "total_patients": total_patients,
        "total_assessments": total_assessments,
        "high_risk_cases": high_risk_cases,
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
    """Export User Statistics as CSV"""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="anonymized_users.csv"'

    writer = csv.writer(response)
    writer.writerow(["Username", "Email", "Role", "Date Joined"])

    users = CustomUser.objects.all()
    for user in users:
        writer.writerow(["User ID", "Role", "Joined Date"])

    return response

@login_required
@user_passes_test(admin_required)
def export_risk_assessments_csv(request):
    """Export Risk Assessment Data as CSV"""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="risk_assessments_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["Patient", "Risk Level", "Risk Probability", "Date"])

    assessments = RiskAssessmentResult.objects.all()
    for assessment in assessments:
        writer.writerow([
            assessment.user.username, assessment.risk_level, 
            f"{assessment.risk_probability:.2f}", assessment.created_at
        ])

    return response

@login_required
@user_passes_test(admin_required)
def export_users_pdf(request):
    """Export User Statistics as PDF"""
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="users_report.pdf"'

    pdf = canvas.Canvas(response, pagesize=letter)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 750, "User Statistics Report")
    
    users = CustomUser.objects.all()
    y = 730
    for user in users:
        # ✅ Use getattr to avoid AttributeError if date_joined is missing
        date_joined = getattr(user, "date_joined", "N/A")  
        pdf.drawString(100, y, f"{user.username} | {user.email} | {user.role} | {date_joined}")
        y -= 20
        if y < 100:
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y = 750

    pdf.showPage()
    pdf.save()
    return response

@login_required
@user_passes_test(admin_required)
def export_risk_assessments_pdf(request):
    """Export Risk Assessment Data as PDF"""
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="risk_assessments_report.pdf"'

    pdf = canvas.Canvas(response, pagesize=letter)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 750, "Risk Assessments Report")

    assessments = RiskAssessmentResult.objects.all()
    y = 730
    for assessment in assessments:
        pdf.drawString(100, y, f"{assessment.user.username} | {assessment.risk_level} | {assessment.risk_probability:.2f} | {assessment.created_at}")
        y -= 20
        if y < 100:
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y = 750

    pdf.showPage()
    pdf.save()
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
def mark_alert_as_read(request, alert_id):
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

    # Apply search filter (by name)
    if search_query:
        patients = [p for p in patients if search_query.lower() in p.username.lower()]

    # Apply age filter (exact match)
    if age_filter:
        patients = [p for p in patients if str(p.age) == age_filter]

    # Apply risk level filter (only patients with risk assessments)
    if risk_level_filter:
        filtered_patients = []
        for patient in patients:
            latest_assessment = patient.risk_assessments.order_by("-created_at").first()
            if latest_assessment and latest_assessment.risk_level == risk_level_filter:
                filtered_patients.append(patient)
        patients = filtered_patients

    return render(request, "doctor/patient_list.html", {
        "patients": patients,
        "search_query": search_query,
        "age_filter": age_filter,
        "risk_level_filter": risk_level_filter
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
    risk_assessments = RiskAssessment.objects.filter(user=patient).order_by("-created_at")

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
    response["Content-Disposition"] = f'attachment; filename="{patient.username}_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["Patient Name", "Email", "Age", "Gender"])
    writer.writerow([patient.username, patient.email, patient.age, patient.gender])

    writer.writerow([])  # Empty row
    writer.writerow(["Date", "Risk Level", "Explanation"])

    risk_assessments = RiskAssessment.objects.filter(user=patient).order_by("-created_at")
    for assessment in risk_assessments:
        writer.writerow([assessment.created_at.strftime("%Y-%m-%d"), assessment.risk_level, assessment.explanation])

    return response

@login_required
def export_patient_pdf(request, patient_id):
    """Doctor - Export Patient Report as PDF"""
    patient = get_object_or_404(CustomUser, id=patient_id, role="patient")

    # Ensure the doctor is assigned to this patient
    if not DoctorPatientAssignment.objects.filter(doctor=request.user, patient=patient).exists():
        return render(request, "error.html", {"message": "Access Denied: You are not assigned to this patient."})

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{patient.username}_report.pdf"'

    pdf = canvas.Canvas(response, pagesize=letter)
    pdf.setFont("Helvetica", 12)

    pdf.drawString(100, 750, f"Patient Report: {patient.username}")
    pdf.drawString(100, 730, f"Email: {patient.email}")
    pdf.drawString(100, 710, f"Age: {patient.age}")
    pdf.drawString(100, 690, f"Gender: {patient.gender}")

    y = 670  # Position for risk assessments
    pdf.drawString(100, y, "Risk Assessments:")
    y -= 20

    risk_assessments = RiskAssessment.objects.filter(user=patient).order_by("-created_at")
    for assessment in risk_assessments:
        pdf.drawString(100, y, f"{assessment.created_at.strftime('%Y-%m-%d')} - {assessment.risk_level}: {assessment.explanation}")
        y -= 20
        if y < 100:  # Move to next page if needed
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y = 750

    pdf.showPage()
    pdf.save()
    return response


@login_required
def patient_detail(request, patient_id):
    """Doctor - View Individual Patient Record & Provide Recommendations"""
    
    if request.user.role != "doctor":
        return render(request, "error.html", {"message": "Access Denied: Only doctors can view patient records."})

    # Fetch patient details & ensure they are assigned to this doctor
    patient = get_object_or_404(CustomUser, id=patient_id, role="Patient")
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
            latest_assessment = risk_assessments.first()  # Link to most recent assessment
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


@login_required
def book_appointment(request, doctor_id):
    """Patient - Book an Appointment with a Doctor"""
    
    doctor = get_object_or_404(CustomUser, id=doctor_id, role="doctor")

    # Ensure the patient is assigned to this doctor
    if not DoctorPatientAssignment.objects.filter(doctor=doctor, patient=request.user).exists():
        return render(request, "error.html", {"message": "Access Denied: You are not assigned to this doctor."})

    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.doctor = doctor
            appointment.patient = request.user
            appointment.status = "Pending"  # Default status
            appointment.save()
            messages.success(request, "Appointment request sent successfully!")
            return redirect("patient_dashboard")

    else:
        form = AppointmentForm()

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
def update_appointment_status(request, appointment_id, status):
    """Doctor - Approve, Cancel, or Reschedule an Appointment"""
    
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
    appointment.status = status
    appointment.save()
    
    messages.success(request, f"Appointment {status.lower()} successfully!")
    return redirect("doctor_appointments")


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
    
    alert = RiskAlert.objects.get(id=alert_id, doctor=request.user)
    alert.is_read = True
    alert.save()

    return redirect("risk_alerts")



@login_required
def patient_risk_chart(request, patient_id):
    """Doctor - View Patient Risk Trend as a Chart"""
    
    if request.user.role != "doctor":
        return render(request, "error.html", {"message": "Access Denied: Only doctors can view risk charts."})

    # Fetch patient details & risk assessments
    patient = get_object_or_404(CustomUser, id=patient_id, role="Patient")
    risk_assessments = RiskAssessment.objects.filter(user=patient).order_by("created_at")

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
    appointments = Appointment.objects.filter(patient=request.user, status="Confirmed").order_by("date", "time")

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