from django.urls import path
from . import views

urlpatterns = [
    # Public Pages
    path('', views.landing_page, name='landing_page'),           # NEW: Front Door
    path('view-routine/', views.view_routine, name='view_routine'), # ALREADY EXISTS
    
    # Authentication
    path('login/', views.user_login, name='login'),              # UPDATED: Moved to /login/
    path('logout/', views.user_logout, name='logout'),
    
    # Dashboards
    path('root-console/', views.superuser_dashboard, name='superuser_dashboard'),
    path('faculty-dashboard/', views.faculty_admin_dashboard, name='faculty_admin_dashboard'),
    path('department-dashboard/', views.dept_admin_dashboard, name='dept_admin_dashboard'),
    path('teacher-space/', views.teacher_dashboard, name='teacher_dashboard'),
    
    # Actions
    path('delete-routine/<int:routine_id>/', views.delete_routine, name='delete_routine'),
]