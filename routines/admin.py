from django.contrib import admin
from .models import (
    Faculty, FacultyAdminProfile, 
    Department, DeptAdminProfile, 
    Teacher, Room, Course, Timeslot, Routine
)

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(FacultyAdminProfile)
class FacultyAdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'faculty')
    list_filter = ('faculty',)
    search_fields = ('user__username', 'faculty__name')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'faculty')
    list_filter = ('faculty',)
    search_fields = ('name', 'faculty__name')

@admin.register(DeptAdminProfile)
class DeptAdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department')
    list_filter = ('department',)
    search_fields = ('user__username', 'department__name')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('teacher_id', 'name', 'department', 'user')
    list_filter = ('department',)
    search_fields = ('name', 'teacher_id', 'user__username')

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'is_online')
    list_filter = ('is_online',)
    search_fields = ('room_number',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'title', 'department')
    list_filter = ('department',)
    search_fields = ('course_code', 'title')

@admin.register(Timeslot)
class TimeslotAdmin(admin.ModelAdmin):
    list_display = ('id', 'start_time', 'end_time')
    sorting = ('start_time',)

@admin.register(Routine)
class RoutineAdmin(admin.ModelAdmin):
    list_display = ('course', 'teacher', 'room', 'timeslot', 'day_of_week', 'semester', 'group_no', 'section')
    list_filter = ('day_of_week', 'semester', 'group_no', 'department', 'room__is_online')
    search_fields = ('course__course_code', 'teacher__name', 'room__room_number')
    
    
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

# 1. Define Inlines for each role profile
class FacultyAdminInline(admin.StackedInline):
    model = FacultyAdminProfile
    can_delete = False
    verbose_name_plural = 'Faculty Admin Role Extension'

class DeptAdminInline(admin.StackedInline):
    model = DeptAdminProfile
    can_delete = False
    verbose_name_plural = 'Department Admin Role Extension'

class TeacherInline(admin.StackedInline):
    model = Teacher
    can_delete = False
    verbose_name_plural = 'Teacher Role Extension'

# 2. Unregister default UserAdmin and Register the customized one
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (FacultyAdminInline, DeptAdminInline, TeacherInline)