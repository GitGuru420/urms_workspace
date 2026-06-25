from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from .models import Routine, Department
from .forms import RoutineForm

def redirect_based_on_role(user):
    if hasattr(user, 'facultyadminprofile'):
        return redirect('faculty_admin_dashboard')
    elif hasattr(user, 'deptadminprofile'):
        return redirect('dept_admin_dashboard')
    elif hasattr(user, 'teacher'):
        return redirect('teacher_dashboard')
    elif user.is_superuser:
        return redirect('/admin/')
    else:
        return redirect('login')

# ==========================================
# AUTHENTICATION VIEWS
# ==========================================
def user_login(request):
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
# TEACHER WORKSPACE MODULES
# ==========================================
@login_required(login_url='login')
def teacher_dashboard(request):
    if not hasattr(request.user, 'teacher'):
         return redirect('login')
         
    teacher = request.user.teacher
    days_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    selected_day = request.GET.get('day_filter', 'All')
    
    # Fetch all routines for this logged-in teacher
    routines_qs = Routine.objects.filter(teacher=teacher).select_related('course', 'room', 'department', 'timeslot')
    total_weekly_classes = routines_qs.count()
    
    # Apply day filter if specified
    if selected_day != 'All':
        filtered_routines = routines_qs.filter(day_of_week=selected_day)
    else:
        filtered_routines = routines_qs

    # Sort chronological by time slots
    filtered_routines = filtered_routines.order_by('timeslot__start_time')
    
    context = {
        'teacher': teacher,
        'total_weekly_classes': total_weekly_classes,
        'days_of_week': days_of_week,
        'selected_day': selected_day,
        'filtered_routines': filtered_routines,
    }
    return render(request, 'routines/teacher_dashboard.html', context)


def view_routine(request):
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    departments = Department.objects.all()
    
    search_triggered = False
    routines = []
    queries = {
        'day': request.GET.get('day', ''),
        'department': request.GET.get('department', ''),
        'semester': request.GET.get('semester', ''),
        'group_no': request.GET.get('group_no', ''),
    }
    
    # Check if form was submitted
    if all([queries['day'], queries['department'], queries['semester'], queries['group_no']]):
        search_triggered = True
        routines = Routine.objects.filter(
            day_of_week=queries['day'],
            department_id=queries['department'],
            semester=queries['semester'],
            group_no=queries['group_no']
        ).select_related('course', 'teacher', 'room', 'timeslot').order_by('timeslot__start_time')
        
    context = {
        'days': days,
        'departments': departments,
        'queries': queries,
        'search_triggered': search_triggered,
        'routines': routines,
    }
    return render(request, 'routines/view_routine.html', context)

# ==========================================
# PLACEHOLDER DASHBOARDS FOR OTHER ROLES
# ==========================================
@login_required(login_url='login')
def faculty_admin_dashboard(request):
    if not hasattr(request.user, 'facultyadminprofile'): return redirect('login')
    return render(request, 'routines/faculty_admin.html')

@login_required(login_url='login')
def dept_admin_dashboard(request):
    if not hasattr(request.user, 'deptadminprofile'): return redirect('login')
    
    dept_admin = request.user.deptadminprofile
    department = dept_admin.department

    if request.method == 'POST':
        form = RoutineForm(request.POST)
        if form.is_valid():
            routine = form.save(commit=False)
            routine.department = department # Auto-assign logged-in admin's department
            
            try:
                routine.clean() # 🔥 TRIGGER CONFLICT ALGORITHM
                routine.save()
                messages.success(request, f"Routine for {routine.course.course_code} successfully scheduled!")
                return redirect('dept_admin_dashboard')
            except ValidationError as e:
                # Catch overlap errors and send to UI
                for error in e.messages:
                    messages.error(request, error)
        else:
            messages.error(request, "Invalid form data. Please check all fields.")
    else:
        form = RoutineForm()

    # Filter dropdowns so Admin only sees their department's courses and teachers
    form.fields['course'].queryset = form.fields['course'].queryset.filter(department=department)
    form.fields['teacher'].queryset = form.fields['teacher'].queryset.filter(department=department)

    # Fetch existing routines for this department
    routines = Routine.objects.filter(department=department).select_related('course', 'teacher', 'room', 'timeslot').order_by('day_of_week', 'timeslot__start_time')

    context = {
        'dept_admin': dept_admin,
        'department': department,
        'form': form,
        'routines': routines,
    }
    return render(request, 'routines/dept_admin.html', context)

@login_required(login_url='login')
def delete_routine(request, routine_id):
    if not hasattr(request.user, 'deptadminprofile'): return redirect('login')
    
    routine = get_object_or_404(Routine, id=routine_id, department=request.user.deptadminprofile.department)
    routine.delete()
    messages.info(request, "Routine slot removed successfully.")
    return redirect('dept_admin_dashboard')