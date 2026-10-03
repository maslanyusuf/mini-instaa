from django import forms

class SharePostForm(forms.Form):
  name = forms.CharField(max_length=100)
  email = forms.EmailField()
  to = forms.EmailField()
  comments = forms.CharField(required=False, widget=forms.Textarea)


