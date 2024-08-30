from django import forms
from django.contrib.auth import get_user_model
from .models import Address
from accounts.models import CustomUser
from django.contrib.auth.forms import PasswordChangeForm

User = get_user_model()


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'}),
        }

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name.isalpha():
            raise forms.ValidationError("First name should only contain letters.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name.isalpha():
            raise forms.ValidationError("Last name should only contain letters.")
        return last_name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This username is already in use.")
        return username


class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your current password'
        })
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your new password'
        }),
        help_text="Your password must contain at least 8 characters and should not be easily guessable."
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your new password'
        })
    )

    def clean_new_password2(self):
        new_password1 = self.cleaned_data.get('new_password1')
        new_password2 = self.cleaned_data.get('new_password2')
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError("The two password fields must match.")
        return new_password2



class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['street', 'city', 'state', 'pin_code', 'country']
        widgets = {
            'street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your street address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your city'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your state'}),
            'pin_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your pin code'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your country'}),
        }

    def clean_pin_code(self):
        pin_code = self.cleaned_data.get('pin_code')
        if not pin_code.isdigit():
            raise forms.ValidationError("Pin code should contain only digits.")
        if len(pin_code) not in [5, 6]:
            raise forms.ValidationError("Pin code must be 5 or 6 digits long.")
        if pin_code.isspace():
            raise forms.ValidationError("Pin code cannot consist of spaces.")
        return pin_code

    def clean_city(self):
        city = self.cleaned_data.get('city')
        if not city.isalpha():
            raise forms.ValidationError("City name should only contain letters.")
        if len(city) < 2:
            raise forms.ValidationError("City name should be at least 2 characters long.")
        if city.isspace():
            raise forms.ValidationError("City name cannot consist of spaces.")
        return city

    def clean_state(self):
        state = self.cleaned_data.get('state')
        if not state.isalpha():
            raise forms.ValidationError("State name should only contain letters.")
        if len(state) < 2:
            raise forms.ValidationError("State name should be at least 2 characters long.")
        if state.isspace():
            raise forms.ValidationError("State name cannot consist of spaces.")
        return state

    def clean_country(self):
        country = self.cleaned_data.get('country')
        if not country.isalpha():
            raise forms.ValidationError("Country name should only contain letters.")
        if len(country) < 2:
            raise forms.ValidationError("Country name should be at least 2 characters long.")
        if country.isspace():
            raise forms.ValidationError("Country name cannot consist of spaces.")
        return country
