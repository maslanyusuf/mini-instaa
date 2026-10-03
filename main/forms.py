from django import forms
from .models import Comment

class SharePostForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your name',
        }),
        help_text='Enter your name.',
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your email',
        }),
        help_text='Enter your email address.',
    )
    to = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': "Recipient's email",
        }),
        help_text="Enter the recipient's email address.",
    )
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Add a comment (optional)',
        }),
        help_text='Add a comment (optional).',
    )



class CommentForm(forms.ModelForm):
  class Meta:
    model = Comment
    fields = ( 'content',)
    # Add bootstrap classes to the form fields with validation errors
    widgets = {
        'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your comment'}),
    }

    # Add help text to the form fields
    help_texts = {
        'content': 'Enter your comment.',
    }


