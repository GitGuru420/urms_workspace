from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# Helper Function: Smart Role Router
def redirect_based_on_role(user):
    """Checks the user's profile relationships and redirects to their specific dashboard."""
    if hasattr(user, 'facultyadminprofile'):
        return redirect('faculty_admin_dashboard')
    elif hasattr(user, 'deptadminprofile'):
        return redirect('dept_admin_dashboard')
    elif hasattr(user, 'teacher'):
        return redirect('teacher_dashboard')
    elif user.is_superuser:
        return redirect('/admin/') # Superusers go to Django admin
    else:
        return redirect('login') # Fallback for users with no assigned roles

# ==========================================
# AUTHENTICATION VIEWS
# ==========================================

def user_login(request):
    # Prevent logged-in users from seeing the login page
    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)

    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        
        user = authenticate(request, username=u, password=p)
        
        if user is not None:
            login(request, user)
            return redirect_based_on_role(user)
        else:
            messages.error(request, "Invalid Credentials. Access Denied.")
            
    return render(request, 'routines/login.html')

def user_logout(request):
    logout(request)
    messages.info(request, "Securely logged out of the workspace.")
    return redirect('login')

# ==========================================
# DASHBOARD PLACEHOLDER VIEWS
# ==========================================

@login_required(login_url='login')
def faculty_admin_dashboard(request):
    # Security block: Only Faculty Admins allowed
    if not hasattr(request.user, 'facultyadminprofile'):
         return redirect('login')
    return render(request, 'routines/faculty_admin.html')

@login_required(login_url='login')
def dept_admin_dashboard(request):
    # Security block: Only Dept Admins allowed
    if not hasattr(request.user, 'deptadminprofile'):
         return redirect('login')
    return render(request, 'routines/dept_admin.html')

@login_required(login_url='login')
def teacher_dashboard(request):
    # Security block: Only Teachers allowed
    if not hasattr(request.user, 'teacher'):
         return redirect('login')
    return render(request, 'routines/teacher_dashboard.html')