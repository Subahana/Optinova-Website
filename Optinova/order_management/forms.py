from django import forms
from user_profile.models import Address

class OrderForm(forms.Form):
    address = forms.ChoiceField(
        choices=[], 
        required=True,
        label='Select or Add Address',
        help_text='Choose an existing address or add a new one.'
    )
    payment_method = forms.ChoiceField(
        choices=[('COD', 'Cash on Delivery'), ('ONLINE', 'Online Payment')],
        required=True,
        label='Payment Method'
    )
    
    # Fields for adding a new address
    new_street = forms.CharField(
        required=False,
        label='Street Address',
        help_text='Enter a new street address if you choose to add a new address.'
    )
    new_city = forms.CharField(
        required=False,
        label='City'
    )
    new_state = forms.CharField(
        required=False,
        label='State'
    )
    new_pin_code = forms.CharField(
        required=False,
        label='PIN Code'
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(OrderForm, self).__init__(*args, **kwargs)
        
        # Populate address choices
        addresses = Address.objects.filter(user=user)
        self.fields['address'].choices = [
            (address.id, f"{address.street}, {address.city}, {address.state} - {address.pin_code}") 
            for address in addresses
        ] + [('add_new', 'Add New Address')]  # Add "Add New Address" option

    def clean(self):
        cleaned_data = super().clean()
        address = cleaned_data.get('address')
        print("Selected Address:", address)
        print("New Street:", cleaned_data.get('new_street'))
        print("New Pin Code:", cleaned_data.get('new_pin_code'))


        # If 'Add New Address' is selected, validate new address fields
        if address == 'add_new':
            new_street = cleaned_data.get('new_street')
            new_pin_code = cleaned_data.get('new_pin_code')

            if not new_street:
                self.add_error('new_street', 'Street Address is required.')
            if not new_pin_code:
                self.add_error('new_pin_code', 'PIN Code is required.')

        return cleaned_data
