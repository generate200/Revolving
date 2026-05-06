from django import forms
from .models import User, profile
from django.core.validators import FileExtensionValidator
from django.contrib.auth.forms import PasswordResetForm

MAX_FILE_SIZE_MB = 6
class profileForm(forms.ModelForm):
    class Meta:
        model = profile
        fields = ['phone', 'profile_pic', 'address', 'city']
    def clean_profile_pic(self):
        profile_pic = self.cleaned_data.get('profile_pic')
        if profile_pic:
            if profile_pic.size > MAX_FILE_SIZE_MB* 1024 * 1024:  # Limit file size to 2MB
                raise forms.ValidationError(f"File size must be less than {MAX_FILE_SIZE_MB} MB")
        return profile_pic
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['profile_pic'].validators.append(
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])
                                                     )
        

class StyledPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email'
    }))