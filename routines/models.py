from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# ==========================================
# 1. UNIVERSITY HIERARCHY & ROLE MODELS
# ==========================================

class Faculty(models.Model):
    name = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.name

class FacultyAdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.faculty.name} Admin"

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name

class DeptAdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.user.username} - {self.department.name} Admin"

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    teacher_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.teacher_id})"

# ==========================================
# 2. SCHEDULING RESOURCES & CORE MODELS
# ==========================================

class Room(models.Model):
    CLASS_TYPE_CHOICES = [
        ('Theory', 'Theory'),
        ('Lab', 'Lab'),
    ]
    
    # ✅ Scopes the room directly to a Faculty for security isolation
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, null=True, blank=True) 
    room_number = models.CharField(max_length=50, unique=True)
    floor_no = models.CharField(max_length=20, default="1st Floor")
    class_type = models.CharField(max_length=15, choices=CLASS_TYPE_CHOICES, default='Theory')
    capacity = models.IntegerField(default=40, help_text="Maximum student seating capacity")
    is_online = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.room_number} ({self.class_type}) - Cap: {self.capacity}"

class Course(models.Model):
    course_code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.course_code} - {self.title}"

class Timeslot(models.Model):
    name = models.CharField(max_length=50, help_text="e.g., Slot 1 (08:00 AM - 09:30 AM)")
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"

class Routine(models.Model):
    DAYS_OF_WEEK = [
        ('Sunday', 'Sunday'), ('Monday', 'Monday'), ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'),
        ('Friday', 'Friday'), ('Saturday', 'Saturday')
    ]
    
    CLASS_TYPE_CHOICES = [
        ('Theory', 'Theory'),
        ('Lab', 'Lab'),
    ]
    
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    timeslot = models.ForeignKey(Timeslot, on_delete=models.CASCADE)
    
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)
    
    class_type = models.CharField(max_length=10, choices=CLASS_TYPE_CHOICES, default='Theory')
    is_online = models.BooleanField(default=False)
    
    day_of_week = models.CharField(max_length=15, choices=DAYS_OF_WEEK)
    semester = models.IntegerField(help_text="1 to 8")
    group_no = models.CharField(max_length=5, help_text="A, B, C")
    
    section = models.CharField(max_length=10, blank=True, null=True, help_text="e.g., A1, B2 (Only for Lab)")

    def clean(self):
        # ALGORITHM: Conflict Resolution & Double-Booking Prevention
        
        if self.is_online:
            self.room = None 
        else:
            if not self.room:
                raise ValidationError("Conflict: Physical (Offline) classes must select a Room.")
            
            if self.class_type == 'Lab' and self.room.class_type != 'Lab':
                raise ValidationError(f"Warning: Selected room {self.room.room_number} is not a Lab room.")

        teacher_conflict = Routine.objects.filter(
            teacher=self.teacher, day_of_week=self.day_of_week, timeslot=self.timeslot
        ).exclude(pk=self.pk).exists()
        if teacher_conflict:
            raise ValidationError(f"Conflict: Teacher {self.teacher.name} is already scheduled at this time.")

        if not self.is_online and self.room:
            room_conflict = Routine.objects.filter(
                room=self.room, day_of_week=self.day_of_week, timeslot=self.timeslot
            ).exclude(pk=self.pk).exists()
            if room_conflict:
                raise ValidationError(f"Conflict: Room {self.room.room_number} is already booked at this time.")

            if self.class_type == 'Lab' and self.room.capacity < 25:
                raise ValidationError(f"Conflict: Selected Lab room capacity ({self.room.capacity}) is too low for a standard lab section (min 25).")

        batch_conflict = Routine.objects.filter(
            department=self.department,
            semester=self.semester,
            group_no=self.group_no,
            section=self.section,
            day_of_week=self.day_of_week,
            timeslot=self.timeslot
        ).exclude(pk=self.pk).exists()
        if batch_conflict:
            sec_info = f" (Sec: {self.section})" if self.section else ""
            raise ValidationError(f"Conflict: Batch {self.semester}{self.group_no}{sec_info} already has a class scheduled at this time.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        type_str = f"Online {self.class_type}" if self.is_online else f"Offline {self.class_type}"
        return f"{self.course.course_code} | {type_str} | {self.day_of_week} | {self.timeslot}"