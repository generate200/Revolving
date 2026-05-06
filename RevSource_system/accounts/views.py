from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import User
from django.db import IntegrityError
from accounts.forms import profileForm

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:report')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_page = request.GET.get('next', 'dashboard:report')
            return redirect(next_page)
        else:
            messages.error(request, 'Invalid username or password')
    
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
                password=password
            )
        except IntegrityError:
            messages.error(request, "Username already taken.")
            return render(request, "accounts/register.html")

        login(request, user)
        messages.success(request, "Account created successfully.")
        return redirect("index")

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

