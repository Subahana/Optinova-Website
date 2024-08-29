from django import forms
from django.contrib.auth import get_user_model
from .models import Address
from accounts.models import CustomUser

User = get_user_model()


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Enter your username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter your email'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Enter your last name'}),
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
            'first_name': forms.TextInput(attrs={'class': 'profile-input'}),
            'last_name': forms.TextInput(attrs={'class': 'profile-input'}),
            'email': forms.EmailInput(attrs={'class': 'profile-input'}),
        }

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['street', 'city', 'state', 'postal_code', 'country']
        
    def clean_postal_code(self):
        postal_code = self.cleaned_data.get('postal_code')
        if not postal_code.isdigit() or len(postal_code) not in [5, 6]:
            raise forms.ValidationError("Enter a valid postal code.")
        return postal_code

    def clean_city(self):
        city = self.cleaned_data.get('city')
        if not city.isalpha():
            raise forms.ValidationError("City name should only contain letters.")
        return city

    def clean_state(self):
        state = self.cleaned_data.get('state')
        if not state.isalpha():
            raise forms.ValidationError("State name should only contain letters.")
        return state

    def clean_country(self):
        country = self.cleaned_data.get('country')
        if not country.isalpha():
            raise forms.ValidationError("Country name should only contain letters.")
        return country