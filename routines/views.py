from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import Routine, Department, Faculty, FacultyAdminProfile, DeptAdminProfile, Teacher, Room, Timeslot, Course

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
                messages.error(request, f"Validation Failed: Department '{dept_name}' already exists.")
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
                messages.error(request, "All fields are required.")
            elif User.objects.filter(username=username).exists():
                messages.error(request, f"Username '{username}' already exists.")
            else:
                target_dept = get_object_or_404(Department, id=dept_id, faculty=faculty)
                new_user = User.objects.create_user(username=username, password=password)
                DeptAdminProfile.objects.create(user=new_user, department=target_dept)
                messages.success(request, f"Success! Admin account created for {target_dept.name}.")
                return redirect('faculty_admin_dashboard')

        # 🔥 NEW ACTION 3: CREATE SECURITY-SCOPED ROOM
        elif 'create_room' in request.POST:
            room_no = request.POST.get('room_number', '').strip()
            floor = request.POST.get('floor_no', '').strip()
            c_type = request.POST.get('class_type')
            cap = request.POST.get('capacity')
            
            if not room_no or not floor or not c_type or not cap:
                messages.error(request, "All room spec fields are required.")
            elif Room.objects.filter(room_number__iexact=room_no).exists():
                messages.error(request, f"Room '{room_no}' already exists globally.")
            else:
                Room.objects.create(
                    faculty=faculty, # Force injected to lock ownership profile
                    room_number=room_no,
                    floor_no=floor,
                    class_type=c_type,
                    capacity=cap
                )
                messages.success(request, f"Asset Logged! Room {room_no} registered to your faculty deck.")
                return redirect('faculty_admin_dashboard')

    # Fetch Data Scoped Strictly to this Faculty
    departments = Department.objects.filter(faculty=faculty).prefetch_related('deptadminprofile_set__user')
    rooms = Room.objects.filter(faculty=faculty).order_by('floor_no', 'room_number') # ✅ Isolated room deck
    
    # Filters logic for Routine Radar
    selected_dept = request.GET.get('department', 'All')
    selected_day = request.GET.get('day', 'All')
    routines = Routine.objects.filter(department__faculty=faculty)
    
    if selected_dept != 'All': routines = routines.filter(department_id=selected_dept)
    if selected_day != 'All': routines = routines.filter(day_of_week=selected_day)
        
    routines = routines.select_related('course', 'teacher', 'room', 'department', 'timeslot').order_by('day_of_week', 'timeslot__start_time')
    
    stats = {
        'total_depts': departments.count(),
        'total_rooms': rooms.count(), # Dynamic room tracking metric
        'active_classes': routines.count(),
    }
    
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    context = {
        'faculty_admin': faculty_admin,
        'faculty': faculty,
        'departments': departments,
        'rooms': rooms,
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
    parent_faculty = dept.faculty
    
    if request.method == 'POST':
        # FEATURE 1: CREATE TEACHER (With strict unique ID checking)
        if 'create_teacher' in request.POST:
            teacher_id = request.POST.get('teacher_id', '').strip()
            name = request.POST.get('name', '').strip()
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            
            if User.objects.filter(username=username).exists():
                messages.error(request, f"Username '{username}' is already taken. Please choose another.")
            elif Teacher.objects.filter(teacher_id=teacher_id).exists():
                messages.error(request, f"Teacher ID '{teacher_id}' already exists in the system.")
            else:
                new_user = User.objects.create_user(username=username, password=password)
                Teacher.objects.create(user=new_user, name=name, department=dept, teacher_id=teacher_id)
                messages.success(request, f"Success! Teacher {name} ({teacher_id}) created.")
            return redirect('dept_admin_dashboard')
            
        # FEATURE 2: CREATE COURSE
        elif 'create_course' in request.POST:
            code = request.POST.get('course_code', '').strip()
            title = request.POST.get('title', '').strip()
            
            if Course.objects.filter(course_code__iexact=code, department=dept).exists():
                messages.error(request, f"Course '{code}' already exists in your department.")
            else:
                Course.objects.create(course_code=code, title=title, department=dept)
                messages.success(request, f"Course [{code}] successfully added.")
            return redirect('dept_admin_dashboard')
            
        # FEATURE 3: ASSIGN ROUTINE
        elif 'assign_routine' in request.POST:
            course_id = request.POST.get('course_id')
            teacher_id_fk = request.POST.get('teacher_id_fk')
            room_id = request.POST.get('room_id')
            timeslot_id = request.POST.get('timeslot_id')
            semester = request.POST.get('semester')
            group_no = request.POST.get('group_no')
            day = request.POST.get('day_of_week')
            section = request.POST.get('section', '').strip() or "None"
            
            # Fetch objects with security filters (Ensuring they belong to the correct dept/faculty)
            course_obj = get_object_or_404(Course, id=course_id, department=dept)
            teacher_obj = get_object_or_404(Teacher, id=teacher_id_fk, department=dept)
            room_obj = get_object_or_404(Room, id=room_id, faculty=parent_faculty)
            timeslot_obj = get_object_or_404(Timeslot, id=timeslot_id)
            
            Routine.objects.create(
                department=dept,
                course=course_obj,
                teacher=teacher_obj,
                room=room_obj,
                timeslot=timeslot_obj,
                semester=semester,
                group_no=group_no,
                day_of_week=day,
                section=section
            )
            messages.success(request, "Routine block assigned successfully!")
            return redirect('dept_admin_dashboard')

    # FEATURE 4: FETCH DATA WITH STRICT DEPARTMENT ISOLATION
    course_query = request.GET.get('course_search', '').strip()
    courses = Course.objects.filter(department=dept)
    if course_query:
        courses = courses.filter(title__icontains=course_query) | courses.filter(course_code__icontains=course_query)
        
    # ONLY fetch teachers from THIS department
    teachers = Teacher.objects.filter(department=dept).order_by('name') 
    faculty_rooms = Room.objects.filter(faculty=parent_faculty).order_by('floor_no', 'room_number')
    routines = Routine.objects.filter(department=dept).select_related('course', 'teacher', 'room', 'timeslot')
    timeslots = Timeslot.objects.all().order_by('start_time')
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    context = {
        'dept_admin': dept_admin,
        'dept': dept,
        'routines': routines,
        'faculty_rooms': faculty_rooms,
        'courses': courses,
        'teachers': teachers,
        'timeslots': timeslots,
        'days': days,
        'course_search': course_query,
    }
    return render(request, 'routines/dept_admin.html', context)
@login_required(login_url='login')
def teacher_dashboard(request):
    if not hasattr(request.user, 'teacher'):
        return redirect('login')
    teacher = request.user.teacher
    routines = Routine.objects.filter(teacher=teacher).select_related('course', 'room', 'timeslot', 'department')
    return render(request, 'routines/teacher_dashboard.html', {'teacher': teacher, 'routines': routines})

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