from django import forms
from .models import VisionBoard, Checkpoint

class VisionBoardForm(forms.ModelForm):
    """Form for creating/editing vision boards"""
    class Meta:
        model = VisionBoard
        fields = ['title', 'description', 'cover_image', 'points', 'is_public']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your vision title',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describe your vision in detail...',
                'required': True
            }),
            'cover_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'points': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 20,
                'value': 20,
                'required': True
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'title': 'Vision Title',
            'description': 'Vision Details',
            'cover_image': 'Cover Image',
            'points': 'Points (minimum 20)',
            'is_public': 'Make this vision board public'
        }

class CheckpointForm(forms.ModelForm):
    """Form for creating/editing checkpoints"""
    class Meta:
        model = Checkpoint
        fields = ['title', 'description', 'order']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Checkpoint title',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description for this checkpoint'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'value': 0
            })
        }
        labels = {
            'title': 'Checkpoint Title',
            'description': 'Description (Optional)',
            'order': 'Order (0, 1, 2, ...)'
        }

