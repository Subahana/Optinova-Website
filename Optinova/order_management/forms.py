# forms.py

from django import forms
from .models import Address

class OrderForm(forms.Form):
    address_id = forms.ModelChoiceField(queryset=Address.objects.none(), empty_label=None)
    payment_method = forms.ChoiceField(choices=[('COD', 'Cash on Delivery')])

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['address_id'].queryset = Address.objects.filter(user=user)
