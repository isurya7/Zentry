from django import forms
from django.forms import ModelForm
from .models import DailyTask
from datetime import date

class DailyTaskForm(ModelForm):
    class Meta:
        model = DailyTask
        fields = ['title', 'description', 'cover_image', 'date', 
                  'is_public', 'group_task', 'reminder_time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'reminder_time': forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set minimum date to today
        self.fields['date'].widget.attrs['min'] = date.today().isoformat()
        # Make description optional
        self.fields['description'].required = False
        # Remove points field - will be auto-assigned

class TaskReminderForm(ModelForm):
    class Meta:
        model = DailyTask
        fields = ['reminder_time']
        widgets = {
            'reminder_time': forms.TimeInput(attrs={'type': 'time'}),
        }