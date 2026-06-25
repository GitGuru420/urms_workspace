from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Role-based Dashboards
    path('faculty-dashboard/', views.faculty_admin_dashboard, name='faculty_admin_dashboard'),
    path('department-dashboard/', views.dept_admin_dashboard, name='dept_admin_dashboard'),
    path('teacher-space/', views.teacher_dashboard, name='teacher_dashboard'),
]