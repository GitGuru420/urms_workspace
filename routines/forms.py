from django import forms
from .models import Routine

class RoutineForm(forms.ModelForm):
    class Meta:
        model = Routine
        # Amra department auto-fill korbo backend theke, tai ekhane list theke bad dilam
        fields = ['course', 'teacher', 'room', 'timeslot', 'day_of_week', 'semester', 'group_no', 'section']