from django import forms
from .models import Category, Product, ProductImage
import re
from PIL import Image as PILImage
import io


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
        }

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance', None)
        super(CategoryForm, self).__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError("Category name is required.")
        
        if not re.match(r'^[\w\s-]+$', name):
            raise forms.ValidationError("Product name should not contain special characters.")

        if not self.instance or self.instance.name != name:
            if Category.objects.filter(name__iexact=name).exists():
                raise forms.ValidationError("Product with this name already exists.")
        
        return name

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'stock', 'category', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter product description'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter price'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter stock quantity'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance', None)
        super(ProductForm, self).__init__(*args, **kwargs)
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError("Product name is required.")
        
        if not re.match(r'^[\w\s-]+$', name):
            raise forms.ValidationError("Product name should not contain special characters.")

        # Skip validation if editing an existing product with the same name
        if not self.instance or self.instance.name != name:
            if Product.objects.filter(name__iexact=name).exists():
                raise forms.ValidationError("Product with this name already exists.")
        
        return name

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock < 0:
            raise forms.ValidationError("Stock cannot be negative.")
        return stock


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={
                'accept': 'image/*', 
                'class': 'form-control',
                'required': 'true'  
            }),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')

        max_size = 2 * 1024 * 1024  # 2MB
        if image.size > max_size:
            raise forms.ValidationError(f"The image file size cannot exceed {max_size / (1024 * 1024)}MB.")

        valid_mime_types = ['image/jpeg', 'image/png', 'image/webp']
        if image.content_type not in valid_mime_types:
            raise forms.ValidationError("Please upload a JPEG, PNG, or WebP image.")

        # Open the image using Pillow
        img = PILImage.open(image)

        # Crop the image to the center and resize it to 800x800
        width, height = img.size
        new_size = min(width, height)  # Get the smaller dimension
        left = (width - new_size) / 2
        top = (height - new_size) / 2
        right = (width + new_size) / 2
        bottom = (height + new_size) / 2

        # Crop and resize the image
        img = img.crop((left, top, right, bottom))
        img = img.resize((800, 800), PILImage.Resampling.LANCZOS)

        # Save the image back to the file field
        output = io.BytesIO()

        # Correct the format
        img_format = image.name.split('.')[-1].upper()
        if img_format == 'JPG':
            img_format = 'JPEG'

        img.save(output, format=img_format)
        output.seek(0)
        image.file = output

        return image

