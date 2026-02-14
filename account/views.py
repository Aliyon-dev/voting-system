from django.shortcuts import render, redirect, reverse
from .email_backend import EmailBackend
from django.contrib import messages
from voting.models import Voter
from django.contrib.auth import login, logout

from voting.models import Voter, Election

def admin_login(request):
    user = request.user
    if user.is_authenticated:
        if user.is_superuser or user.user_type == '1':
            return redirect(reverse("adminDashboard"))
        else:
            messages.error(request, "Access Denied")
            
    context = {}
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = EmailBackend.authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect(reverse("adminDashboard"))
        else:
            messages.error(request, "Invalid Credentials")
            
    return render(request, "voting/admin_login.html", context)


def voter_login(request):
    return redirect(reverse("index")) 

def choose_election(request):
    return redirect(reverse('index'))




def account_logout(request):
    # Admin Logout
    if request.user.is_authenticated:
        logout(request)
    
    # Voter Logout
    if 'voter_id' in request.session:
        del request.session['voter_id']

    messages.success(request, "Thank you for visiting us!")
    return redirect(reverse("account_login"))
