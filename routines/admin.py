from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    Faculty, Department, FacultyAdminProfile, 
    DeptAdminProfile, Teacher, Room, Course, Timeslot, Routine
)

# ==========================================
# 1. SMART INLINE ROLE ASSIGNMENT
# ==========================================
# Database-e user create korar shomoy nichei ei dropdown block gulo manually add hobe.
class FacultyAdminInline(admin.StackedInline):
    model = FacultyAdminProfile
    extra = 0
    verbose_name_plural = 'Faculty Admin Role Extension'

class DeptAdminInline(admin.StackedInline):
    model = DeptAdminProfile
    extra = 0
    verbose_name_plural = 'Department Admin Role Extension'

class TeacherInline(admin.StackedInline):
    model = Teacher
    extra = 0
    verbose_name_plural = 'Teacher Role Extension'


class CustomUserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'is_staff', 'is_superuser']
    list_filter = ['is_staff', 'is_superuser']
    inlines = [FacultyAdminInline, DeptAdminInline, TeacherInline] # 🔥 This adds the role creation inline form!

# Unregister original design and secure customized handler
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, CustomUserAdmin)


# ==========================================
# 2. CORE MASTER DATASET PANELS
# ==========================================

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'faculty']
    list_filter = ['faculty']
    search_fields = ['name', 'faculty__name']


@admin.register(FacultyAdminProfile)
class FacultyAdminProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'faculty']
    list_filter = ['faculty']
    search_fields = ['user__username', 'faculty__name']


@admin.register(DeptAdminProfile)
class DeptAdminProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'department']
    list_filter = ['department']
    search_fields = ['user__username', 'department__name']


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['teacher_id', 'name', 'department', 'user']
    search_fields = ['name', 'teacher_id', 'user__username']
    list_filter = ['department']


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['room_number', 'is_online']
    list_filter = ['is_online']
    search_fields = ['room_number']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'title', 'department']
    search_fields = ['course_code', 'title']
    list_filter = ['department']


@admin.register(Timeslot)
class TimeslotAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'start_time', 'end_time']
    ordering = ['start_time']


@admin.register(Routine)
class RoutineAdmin(admin.ModelAdmin):
    list_display = ['course', 'teacher', 'room', 'timeslot', 'day_of_week', 'semester', 'group_no', 'section', 'department']
    list_filter = ['day_of_week', 'semester', 'group_no', 'department', 'room__is_online']
    search_fields = ['group_no', 'course__course_code', 'teacher__name', 'room__room_number']