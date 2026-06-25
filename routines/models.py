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
    room_number = models.CharField(max_length=50, unique=True)
    is_online = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.room_number} {'(Online)' if self.is_online else ''}"

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
    
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    timeslot = models.ForeignKey(Timeslot, on_delete=models.CASCADE)
    
    day_of_week = models.CharField(max_length=15, choices=DAYS_OF_WEEK)
    semester = models.IntegerField(help_text="1 to 8")
    group_no = models.CharField(max_length=5, help_text="A, B, C")
    section = models.CharField(max_length=10, default="None", help_text="Lab Sec 1, 2 or None for Theory")

    def clean(self):
        # ALGORITHM: Conflict Resolution & Double-Booking Prevention
        
        # 1. Teacher Overlap: Teacher cannot be in two places at once.
        teacher_conflict = Routine.objects.filter(
            teacher=self.teacher, day_of_week=self.day_of_week, timeslot=self.timeslot
        ).exclude(pk=self.pk).exists()
        if teacher_conflict:
            raise ValidationError(f"Conflict: Teacher {self.teacher.name} is already scheduled at this time.")

        # 2. Room Overlap: Physical rooms cannot double-book.
        if not self.room.is_online:
            room_conflict = Routine.objects.filter(
                room=self.room, day_of_week=self.day_of_week, timeslot=self.timeslot
            ).exclude(pk=self.pk).exists()
            if room_conflict:
                raise ValidationError(f"Conflict: Room {self.room.room_number} is already booked at this time.")

        # 3. Batch Overlap: Same semester/group/section cannot have two classes at once.
        batch_conflict = Routine.objects.filter(
            department=self.department,
            semester=self.semester,
            group_no=self.group_no,
            section=self.section,
            day_of_week=self.day_of_week,
            timeslot=self.timeslot
        ).exclude(pk=self.pk).exists()
        if batch_conflict:
            raise ValidationError(f"Conflict: Batch {self.semester}{self.group_no} (Sec: {self.section}) already has a class scheduled at this time.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.course.course_code} | {self.day_of_week} | {self.timeslot}"