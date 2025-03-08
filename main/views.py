from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def home(request):
    return HttpResponse("<h1>Welcome to My Website!</h1>")

def home(request):
    return render(request, 'home.html')

def register_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("role")

        user = CustomUser.objects.create_user(username=username, email=email, password=password, role=role)

        # Assign permissions after user is created
        assign_permissions(user)

        login(request, user)
        return redirect("dashboard")

    return render(request, "register.html")