from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import Routine, Department, Faculty, FacultyAdminProfile, DeptAdminProfile, Teacher

# ==========================================
# PUBLIC & AUTHENTICATION VIEWS
# ==========================================
def landing_page(request):
    return render(request, 'routines/index.html')

def redirect_based_on_role(user):
    if user.is_superuser:
        return redirect('superuser_dashboard')
    elif hasattr(user, 'facultyadminprofile'):
        return redirect('faculty_admin_dashboard')
    elif hasattr(user, 'deptadminprofile'):
        return redirect('dept_admin_dashboard')
    elif hasattr(user, 'teacher'):
        return redirect('teacher_dashboard')
    return redirect('landing_page')

def user_login(request):
    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)
        
    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '').strip()
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect_based_on_role(user)
        else:
            messages.error(request, "Invalid credentials. Unauthorized clearance denied.")
    return render(request, 'routines/login.html')

def user_logout(request):
    logout(request)
    return redirect('landing_page')

# ==========================================
# SUPERUSER MASTER DASHBOARD
# ==========================================
@login_required(login_url='login')
def superuser_dashboard(request):
    if not request.user.is_superuser:
        return redirect('login')
        
    faculties = Faculty.objects.all()
    selected_faculty_id = request.GET.get('faculty', 'All')
    selected_dept_id = request.GET.get('department', 'All')
    selected_day = request.GET.get('day', 'All')
    
    departments = Department.objects.all()
    routines = Routine.objects.all()
    
    if selected_faculty_id != 'All':
        departments = departments.filter(faculty_id=selected_faculty_id)
        routines = routines.filter(department__faculty_id=selected_faculty_id)
        
    if selected_dept_id != 'All':
        routines = routines.filter(department_id=selected_dept_id)
        
    if selected_day != 'All':
        routines = routines.filter(day_of_week=selected_day)
        
    routines = routines.select_related('course', 'teacher', 'room', 'department', 'timeslot')
    
    stats = {
        'total_faculties': faculties.count(),
        'total_depts': Department.objects.count(),
        'active_classes': Routine.objects.count(),
    }
    
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    context = {
        'faculties': faculties,
        'departments': departments,
        'routines': routines,
        'selected_faculty': selected_faculty_id,
        'selected_dept': selected_dept_id,
        'selected_day': selected_day,
        'stats': stats,
        'days': days,
    }
    return render(request, 'routines/superuser.html', context)

# ==========================================
# UPGRADED: FACULTY ADMIN WORKSPACE (With Create Dept & Admin Lookup)
# ==========================================
@login_required(login_url='login')
def faculty_admin_dashboard(request):
    if not hasattr(request.user, 'facultyadminprofile'): 
        return redirect('login')
    
    faculty_admin = request.user.facultyadminprofile
    faculty = faculty_admin.faculty
    
    # Process POST Forms
    if request.method == 'POST':
        # 1. Action: CREATE DEPARTMENT
        if 'create_department' in request.POST:
            dept_name = request.POST.get('dept_name', '').strip()
            if not dept_name:
                messages.error(request, "Department name cannot be empty.")
            elif Department.objects.filter(name__iexact=dept_name).exists():
                messages.error(request, f"Validation Failed: Department '{dept_name}' already exists globally.")
            else:
                Department.objects.create(name=dept_name, faculty=faculty)
                messages.success(request, f"Success! Department '{dept_name}' registered under {faculty.name}.")
                return redirect('faculty_admin_dashboard')

        # 2. Action: CREATE DEPARTMENT ADMIN 
        elif 'create_dept_admin' in request.POST:
            dept_id = request.POST.get('department_id')
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            
            if not dept_id or not username or not password:
                messages.error(request, "All fields are strictly required.")
            elif User.objects.filter(username=username).exists():
                messages.error(request, f"Username '{username}' already exists globally.")
            else:
                target_dept = get_object_or_404(Department, id=dept_id, faculty=faculty)
                new_user = User.objects.create_user(username=username, password=password)
                DeptAdminProfile.objects.create(user=new_user, department=target_dept)
                messages.success(request, f"Success! Dept Admin token linked to {target_dept.name}.")
                return redirect('faculty_admin_dashboard')

    # Fetch Data Scoped Strictly to this Faculty
    departments = Department.objects.filter(faculty=faculty).prefetch_related('deptadminprofile_set__user')
    
    # Filters logic
    selected_dept = request.GET.get('department', 'All')
    selected_day = request.GET.get('day', 'All')
    routines = Routine.objects.filter(department__faculty=faculty)
    
    if selected_dept != 'All':
        routines = routines.filter(department_id=selected_dept)
    if selected_day != 'All':
        routines = routines.filter(day_of_week=selected_day)
        
    routines = routines.select_related('course', 'teacher', 'room', 'department', 'timeslot').order_by('day_of_week', 'timeslot__start_time')
    
    stats = {
        'total_depts': departments.count(),
        'active_classes': routines.count(),
    }
    
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    context = {
        'faculty_admin': faculty_admin,
        'faculty': faculty,
        'departments': departments,
        'routines': routines,
        'selected_dept': selected_dept,
        'selected_day': selected_day,
        'stats': stats,
        'days': days,
    }
    return render(request, 'routines/faculty_admin.html', context)

# ==========================================
# DEPENDENT INNER WORKSPACES (Unchanged)
# ==========================================
@login_required(login_url='login')
def dept_admin_dashboard(request):
    if not hasattr(request.user, 'deptadminprofile'):
        return redirect('login')
    dept_admin = request.user.deptadminprofile
    dept = dept_admin.department
    routines = Routine.objects.filter(department=dept).select_related('course', 'teacher', 'room', 'timeslot')
    return render(request, 'routines/dept_admin.html', {'dept_admin': dept_admin, 'dept': dept, 'routines': routines})

@login_required(login_url='login')
def teacher_dashboard(request):
    if not hasattr(request.user, 'teacher'):
        return redirect('login')
    teacher = request.user.teacher
    routines = Routine.objects.filter(teacher=teacher).select_related('course', 'room', 'timeslot', 'department')
    return render(request, 'routines/teacher.html', {'teacher': teacher, 'routines': routines})

@login_required(login_url='login')
def delete_routine(request, routine_id):
    routine = get_object_or_404(Routine, id=routine_id)
    routine.delete()
    messages.success(request, "Routine block wiped successfully.")
    return redirect_based_on_role(request.user)

def view_routine(request):
    departments = Department.objects.all()
    selected_dept = request.GET.get('department')
    selected_semester = request.GET.get('semester')
    selected_group = request.GET.get('group_no')
    routines = Routine.objects.all()
    if selected_dept: routines = routines.filter(department_id=selected_dept)
    if selected_semester: routines = routines.filter(semester=selected_semester)
    if selected_group: routines = routines.filter(group_no=selected_group)
    return render(request, 'routines/view_routine.html', {'departments': departments, 'routines': routines})