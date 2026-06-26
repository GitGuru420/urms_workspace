from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import Routine, Department, Faculty, FacultyAdminProfile, DeptAdminProfile, Teacher, Room, Timeslot, Course
import csv
from django.http import HttpResponse

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
    # 1. Get Logged-in Faculty Admin Profile and their assigned Faculty
    faculty_profile = get_object_or_404(FacultyAdminProfile, user=request.user)
    current_faculty = faculty_profile.faculty  # This locks the scope (e.g., Engineering Faculty)

    # 2. Handle Form Submissions (POST Requests) with Faculty Lockdown Security
    if request.method == 'POST':
        action = request.POST.get('action')

        # Action A: Create Room (Faculty Locked)
        if action == 'create_room':
            room_number = request.POST.get('room_number')
            capacity = request.POST.get('capacity')
            is_online = request.POST.get('is_online') == 'on'
            Room.objects.create(
                room_number=room_number, 
                capacity=capacity, 
                is_online=is_online,
                faculty=current_faculty
            )
            return redirect('faculty_admin_dashboard')

        # Action B: Create Department (Automatically bind to this admin's faculty!)
        elif action == 'create_department':
            name = request.POST.get('name')
            code = request.POST.get('code')
            # SECURITY FIX: Auto assigning the current faculty so they can't create depts for others
            Department.objects.create(name=name, code=code, faculty=current_faculty)
            return redirect('faculty_admin_dashboard')

        # Action C: Create Dept Admin Profile
        elif action == 'create_dept_admin':
            username = request.POST.get('username')
            password = request.POST.get('password')
            dept_id = request.POST.get('department')
            
            # Security Check: Ensure target dept belongs to this admin's faculty
            dept = get_object_or_404(Department, id=dept_id, faculty=current_faculty)
            user = User.objects.create_user(username=username, password=password)
            from .models import DeptAdminProfile
            DeptAdminProfile.objects.create(user=user, department=dept)
            return redirect('faculty_admin_dashboard')

        # Action D: Create Course
        elif action == 'create_course':
            course_code = request.POST.get('course_code')
            title = request.POST.get('title')
            dept_id = request.POST.get('department')
            
            # Security Check: Ensure target dept belongs to this admin's faculty
            dept = get_object_or_404(Department, id=dept_id, faculty=current_faculty)
            Course.objects.create(course_code=course_code, title=title, department=dept)
            return redirect('faculty_admin_dashboard')

        # Action E: Super Admin Class Assignment
        elif action == 'assign_class':
            dept_id = request.POST.get('department')
            # Security Check: Double-checking ownership before committing to DB
            dept = get_object_or_404(Department, id=dept_id, faculty=current_faculty)
            
            teacher = get_object_or_404(Teacher, id=request.POST.get('teacher'), department__faculty=current_faculty)
            course = get_object_or_404(Course, id=request.POST.get('course'), department__faculty=current_faculty)
            room = get_object_or_404(Room, id=request.POST.get('room'))
            timeslot = get_object_or_404(Timeslot, id=request.POST.get('timeslot'))
            
            Routine.objects.create(
                department=dept,
                teacher=teacher,
                course=course,
                room=room,
                timeslot=timeslot,
                day_of_week=request.POST.get('day_of_week'),
                semester=request.POST.get('semester'),
                group_no=request.POST.get('group_no')
            )
            return redirect('faculty_admin_dashboard')

    # 3. GET Method: DATA ISOLATION LAYER (Locking Querysets to current faculty)
    # Only pull departments belonging to this specific Faculty Admin
    departments = Department.objects.filter(faculty=current_faculty).order_by('name')
    
    # Filter courses and teachers that only belong to this Faculty's departments
    courses = Course.objects.filter(department__in=departments).order_by('course_code')
    teachers = Teacher.objects.filter(department__in=departments).order_by('name')
    
    # Rooms and Timeslots can remain globally accessible for scheduling availability
    rooms = Room.objects.filter(faculty=current_faculty).order_by('room_number')
    timeslots = Timeslot.objects.all().order_by('start_time')
    days = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    # 4. Advanced Isolated Search Hub
    search_dept = request.GET.get('search_dept')
    search_day = request.GET.get('search_day')
    search_room = request.GET.get('search_room')
    search_time = request.GET.get('search_time')
    search_teacher = request.GET.get('search_teacher')

    master_routines = None  # Default hidden state

    if any([search_dept, search_day, search_room, search_time, search_teacher]):
        # BASE FILTER CRITICAL SAFEGUARD: Only search routines within this faculty's departments
        master_routines = Routine.objects.filter(department__in=departments).select_related(
            'course', 'teacher', 'room', 'timeslot', 'department'
        )
        
        if search_dept:
            master_routines = master_routines.filter(department_id=search_dept)
        if search_day:
            master_routines = master_routines.filter(day_of_week=search_day)
        if search_room:
            master_routines = master_routines.filter(room_id=search_room)
        if search_time:
            master_routines = master_routines.filter(timeslot_id=search_time)
        if search_teacher:
            master_routines = master_routines.filter(teacher_id=search_teacher)

    # 5. CSV Export Engine (Isolated Data Output Only)
    if request.GET.get('export_csv') == '1' and master_routines is not None:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{current_faculty.name}_Routine_Grid.csv"'
        writer = csv.writer(response)
        writer.writerow(['Department', 'Day', 'Time', 'Course Code', 'Course Title', 'Teacher', 'Room', 'Semester', 'Group'])
        
        for r in master_routines:
            writer.writerow([r.department.name, r.day_of_week, f"{r.timeslot.start_time}", r.course.course_code, r.course.title, r.teacher.name, r.room.room_number, r.semester, r.group_no])
        return response

    context = {
        'faculty_profile': faculty_profile,
        'current_faculty': current_faculty,
        'departments': departments,
        'rooms': rooms,
        'teachers': teachers,
        'courses': courses,
        'timeslots': timeslots,
        'days': days,
        'master_routines': master_routines,
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
        # FEATURE 1: CREATE TEACHER
        if 'create_teacher' in request.POST:
            teacher_id = request.POST.get('teacher_id', '').strip()
            name = request.POST.get('name', '').strip()
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            
            if User.objects.filter(username=username).exists():
                messages.error(request, f"Username '{username}' is already taken.")
            elif Teacher.objects.filter(teacher_id=teacher_id).exists():
                messages.error(request, f"Teacher ID '{teacher_id}' already exists.")
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
                messages.error(request, f"Course '{code}' already exists.")
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
            
            course_obj = get_object_or_404(Course, id=course_id, department=dept)
            teacher_obj = get_object_or_404(Teacher, id=teacher_id_fk, department=dept)
            room_obj = get_object_or_404(Room, id=room_id, faculty=parent_faculty)
            timeslot_obj = get_object_or_404(Timeslot, id=timeslot_id)
            
            Routine.objects.create(
                department=dept, course=course_obj, teacher=teacher_obj,
                room=room_obj, timeslot=timeslot_obj, semester=semester,
                group_no=group_no, day_of_week=day, section=section
            )
            messages.success(request, "Routine block assigned successfully!")
            return redirect('dept_admin_dashboard')

    # FEATURE 4: ADVANCED ROUTINE SEARCH
    routines = Routine.objects.filter(department=dept).select_related('course', 'teacher', 'room', 'timeslot')
    
    search_day = request.GET.get('search_day', '')
    search_room = request.GET.get('search_room', '')
    search_time = request.GET.get('search_time', '')
    search_teacher = request.GET.get('search_teacher', '')
    
    if search_day:
        routines = routines.filter(day_of_week=search_day)
    if search_room:
        routines = routines.filter(room_id=search_room)
    if search_time:
        routines = routines.filter(timeslot_id=search_time)
    if search_teacher:
        routines = routines.filter(teacher_id=search_teacher)

    # FEATURE 5: CSV/EXCEL EXPORT
    if request.GET.get('export_csv') == '1':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{dept.name}_Routine_Export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Day', 'Time', 'Course Code', 'Course Title', 'Teacher', 'Room', 'Semester', 'Group'])
        
        for r in routines:
            writer.writerow([
                r.day_of_week, 
                f"{r.timeslot.start_time.strftime('%I:%M %p')} - {r.timeslot.end_time.strftime('%I:%M %p')}",
                r.course.course_code, r.course.title, r.teacher.name, 
                r.room.room_number, r.semester, r.group_no
            ])
        return response

    # Basic queries for dropdowns and lists
    courses = Course.objects.filter(department=dept)
    teachers = Teacher.objects.filter(department=dept).order_by('name') 
    faculty_rooms = Room.objects.filter(faculty=parent_faculty).order_by('floor_no', 'room_number')
    timeslots = Timeslot.objects.all().order_by('start_time')
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    context = {
        'dept_admin': dept_admin, 'dept': dept, 'routines': routines,
        'faculty_rooms': faculty_rooms, 'courses': courses, 'teachers': teachers,
        'timeslots': timeslots, 'days': days,
    }
    return render(request, 'routines/dept_admin.html', context)

""" TEACHER DASHBOARD VERSION-1 DONE"""
@login_required(login_url='login')
def teacher_dashboard(request):
    # Get Logged-in Teacher Info
    teacher = get_object_or_404(Teacher, user=request.user)
    # Count Total Class In a Week
    total_weekly_classes = Routine.objects.filter(teacher=teacher).count()

    # LOGIC: Advanced Search Parameters
    days = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    timeslots = Timeslot.objects.all().order_by('start_time')

    search_day = request.GET.get('search_day')
    search_time = request.GET.get('search_time')

    # Base query for Global Master Routine
    master_routines = Routine.objects.filter(teacher=teacher).select_related('course', 'room', 'timeslot', 'department')

    # Apply filters dynamically if user searched for anything
    if search_day:
        master_routines = master_routines.filter(day_of_week=search_day)
    if search_time:
        master_routines = master_routines.filter(timeslot_id=search_time)

    # LOGIC: CSV Export Handler
    if request.GET.get('export_csv') == '1':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{teacher.name}_Routine_Export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Day', 'Time', 'Course Code', 'Course Title', 'Room', 'Semester', 'Group'])
        
        for r in master_routines:
            writer.writerow([
                r.day_of_week,
                f"{r.timeslot.start_time.strftime('%I:%M %p')} - {r.timeslot.end_time.strftime('%I:%M %p')}",
                r.course.course_code,
                r.course.title,
                f"Room {r.room.room_number}" if not r.room.is_online else "Online",
                r.semester,
                r.group_no
            ])
        return response

    context = {
        'teacher': teacher,
        'total_weekly_classes': total_weekly_classes,
        'days': days,
        'timeslots': timeslots,
        'master_routines': master_routines,
    }
    
    return render(request, 'routines/teacher_dashboard.html', context)

@login_required(login_url='login')
def delete_routine(request, routine_id):
    routine = get_object_or_404(Routine, id=routine_id)
    routine.delete()
    messages.success(request, "Routine block wiped successfully.")
    return redirect_based_on_role(request.user)

# View Routine Without
def view_routine(request):
    # 1. Backend theke dynamic days ar departments load kora
    days = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    departments = Department.objects.all().order_by('name')
    
    # 2. Get Form Inputs
    day = request.GET.get('day', '').strip()
    department_id = request.GET.get('department', '').strip()
    semester = request.GET.get('semester', '').strip()
    group_no = request.GET.get('group_no', '').strip()
    
    routines = None
    search_triggered = False
    
    # 3. Validation: Sobgulo field match korlei shudhu search hobe (Tomar requirement)
    if day and department_id and semester and group_no:
        search_triggered = True
        routines = Routine.objects.filter(
            day_of_week=day,
            department_id=department_id,
            semester=semester,
            group_no=group_no
        ).select_related('course', 'teacher', 'room', 'timeslot')
    
    # Pack parameters to retain values after form submission
    queries = {
        'day': day,
        'department': department_id,
        'semester': semester,
        'group_no': group_no
    }
    
    context = {
        'days': days,
        'departments': departments,
        'routines': routines,
        'search_triggered': search_triggered,
        'queries': queries
    }
    
    return render(request, 'routines/view_routine.html', context)