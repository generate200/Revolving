from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import User
from django.db import IntegrityError
from accounts.forms import profileForm
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.core.mail import send_mail
from .tokens import email_verification_token


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:report')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "Please verify your email before logging in.")
                return render(request, 'accounts/login.html')

            login(request, user)
            messages.success(request, 'Logged in successfully')
            return redirect('dashboard:report')

        else:
            # ✅ HANDLE INVALID LOGIN
            messages.error(request, 'Invalid email or password')

    # ✅ ALWAYS RETURN SOMETHING
    return render(request, 'accounts/login.html')


@require_http_methods(["GET", "POST"])
@login_required(login_url='accounts:login')
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out')
    return redirect('accounts:login')


def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirmation = request.POST.get("confirmation")

        if password != confirmation:
            messages.error(request, "Passwords must match.")
            return render(request, "accounts/register.html")

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=False
            )
            send_verification_email(request, user)
        except IntegrityError:
            messages.error(request, "Username already taken.")
            return render(request, "accounts/register.html")

    
        messages.success(request, "Account created. Please check your email to verify your account.")
        return redirect('accounts:login')

    return render(request, "accounts/register.html")

def profile_view(request):
    user_instance=request.user
    try:
        profile_instance=user_instance.profile
    except:
        profile_instance=None
    if request.method == "POST":
        form=profileForm(request.POST,request.FILES,instance=profile_instance)
        if form.is_valid():
            new_profile=form.save(commit=False)
            new_profile.user=user_instance
            new_profile.save()
            messages.success(request,"Profile updated successfully")
            return redirect('accounts:profile')
    else:
        form=profileForm(instance=profile_instance)
    context={
        'form':form,
        'profile':profile_instance
    }
            
    return render(request,'accounts/profile.html',context)

def update_profile(request):
    user_instance=request.user
    try:
        profile_instance=user_instance.profile
    except:
        profile_instance=None
    if request.method == "POST":
        form=profileForm(request.POST,request.FILES,instance=profile_instance)
        if form.is_valid():
            new_profile=form.save(commit=False)
            new_profile.user=user_instance
            new_profile.save()
            messages.success(request,"Profile updated successfully")
            return redirect('accounts:profile')
    else:
        form=profileForm(instance=profile_instance)
    context={
        'form':form,
        'profile':profile_instance
    }
            
    return render(request,'accounts/profile.html',context)

def send_verification_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)

    link = request.build_absolute_uri(
        reverse('accounts:email_confirm', kwargs={'uidb64': uid, 'token': token})
    )

    send_mail(
        'Verify your email',
        f'Click the link to verify your email: {link}',
        'revolvingsourcesmail@gmail.com',
        [user.email],
    )

def confirm_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user and email_verification_token.check_token(user, token):
        user.is_active = True  # or custom field like is_verified
        user.save()
        return redirect('accounts:login')
    else:
        return redirect('/accounts/login/?signal=email_auth_success')