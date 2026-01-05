from django import forms

class EmailReplyForm(forms.Form):
    subject = forms.CharField(max_length=255, required=True)
    body = forms.CharField(widget=forms.Textarea, required=True)
