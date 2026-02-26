from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm
from .models import UserProfile
from .utils import dashboard_url_for_user


def register(request):
    if request.user.is_authenticated:
        return redirect(dashboard_url_for_user(request.user))

    if request.method == "POST":
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = form.cleaned_data["role"]
            if profile.role == UserProfile.Role.STUDENT and not form.cleaned_data.get("face_image"):
                form.add_error("face_image", "Facial image is required for student registration.")
                return render(request, "accounts/register.html", {"form": form})
            profile.face_image = form.cleaned_data.get("face_image")
            profile.save(update_fields=["role", "face_image"])
            auth_login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect(dashboard_url_for_user(user))
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(dashboard_url_for_user(request.user))

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user:
                profile = getattr(user, "profile", None)
                if profile and profile.is_student and not profile.face_image:
                    messages.error(request, "Student account requires a registered facial image.")
                    return render(request, "accounts/login.html", {"form": form})
                auth_login(request, user)
                messages.success(request, "Logged in successfully.")
                return redirect(dashboard_url_for_user(user))
        messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    auth_logout(request)
    messages.info(request, "Logged out.")
    return redirect("index")
