from django import forms
from .models import Product,ProductImage,ProductVariant,Category
import re
from PIL import Image as PILImage
import io
import sys
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile


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
        
        if re.fullmatch(r'\d+', name):
            raise forms.ValidationError("Category name cannot consist of numbers only.")
        
        if not re.match(r'^[\w\s-]+$', name):
            raise forms.ValidationError("Category name should not contain special characters.")
        
        if len(name) < 4:
            raise forms.ValidationError("Category name must be at least 4 characters long.")
        
        if not self.instance or self.instance.name != name:
            if Category.objects.filter(name__iexact=name).exists():
                raise forms.ValidationError("Category with this name already exists.")
        
        return name

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'base_price', 'category']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Product name'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'base_price': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance', None)  # Get the instance (for edit case)
        super(ProductForm, self).__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        
        # Validate name length
        if len(name) < 3:
            raise ValidationError("Product name must be at least 3 characters long.")
        
        # Uniqueness check, excluding the current product when editing
        if Product.objects.filter(name__iexact=name).exclude(id=self.instance.id).exists():
            raise ValidationError("A product with this name already exists.")
        
        return name

    def clean_base_price(self):
        base_price = self.cleaned_data.get('base_price')
        if base_price is None or base_price <= 0:
            raise ValidationError("Base price must be greater than zero.")
        return base_price

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description:
            raise ValidationError("Description cannot be empty.")
        if len(description) < 10:
            raise ValidationError("Description must be at least 10 characters long.")
        return description
    
    def clean_category(self):
        category = self.cleaned_data.get('category')

        if category and not category.is_active:
            raise forms.ValidationError("You cannot add a product to an inactive category.")
        
        return category

class ProductVariantForm(forms.ModelForm):
    COLORS = [
        ('', 'Select a color'),
        ('red', 'Red'),
        ('pink', 'Pink'),
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('Black', 'Black'),
        ('White', 'White'),
        ('Gold', 'Gold'),
        ('Silver', 'Silver'),
    ]

    color = forms.ChoiceField(
        choices=COLORS,
        widget=forms.Select(attrs={'class': 'form-control'}),
        error_messages={'required': 'Please select a color'}
    )

    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter price'}),
        error_messages={
            'required': 'Please enter a valid price',
            'invalid': 'Enter a valid decimal number for the price'
        }
    )

    stock = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter stock quantity'}),
        min_value=0,
        error_messages={
            'required': 'Please enter the stock quantity',
            'invalid': 'Enter a valid number',
            'min_value': 'Stock cannot be negative'
        }
    )

    is_main_variant = forms.BooleanField(required=False, label="Set as Main Variant")

    class Meta:
        model = ProductVariant
        fields = ['color', 'price', 'stock', 'is_main_variant']

    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        super(ProductVariantForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        color = cleaned_data.get('color')
        is_main_variant = cleaned_data.get('is_main_variant')

        if color:
            if ProductVariant.objects.filter(product=self.product, color=color).exclude(id=self.instance.id).exists():
                self.add_error('color', "The color '{}' is already used for another variant of this product.".format(color))

        if is_main_variant:
            if ProductVariant.objects.filter(product=self.product, is_main_variant=True).exclude(id=self.instance.id).exists():
                self.add_error(None, "A main variant already exists for this product. Only one main variant is allowed.")

        return cleaned_data



class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control',
                'required': 'true',
            }),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')

        if not image:
            raise ValidationError("Please upload an image.")

        # Check image size
        max_size = 2 * 1024 * 1024  # 2MB
        if image.size > max_size:
            raise ValidationError(f"The image file size cannot exceed {max_size / (1024 * 1024)}MB.")

        # Check image format
        valid_mime_types = ['image/jpeg', 'image/png', 'image/webp']
        if image.content_type not in valid_mime_types:
            raise ValidationError("Please upload a JPEG, PNG, or WebP image.")

        try:
            # Open the image using Pillow
            img = PILImage.open(image)

            # Crop the image to the center and resize it to 800x800
            width, height = img.size
            new_size = min(width, height)
            left = (width - new_size) / 2
            top = (height - new_size) / 2
            right = (width + new_size) / 2
            bottom = (height + new_size) / 2

            img = img.crop((left, top, right, bottom))
            img = img.resize((800, 800), PILImage.Resampling.LANCZOS)

            # Save the image back to a BytesIO object
            output = io.BytesIO()
            img_format = image.name.split('.')[-1].upper()
            if img_format == 'JPG':
                img_format = 'JPEG'

            img.save(output, format=img_format)
            output.seek(0)

            # Create a new InMemoryUploadedFile to replace the original
            image = InMemoryUploadedFile(output, 'image', image.name, image.content_type, sys.getsizeof(output), None)

        except Exception as e:
            raise ValidationError(f"Error processing the image: {e}")

        if not image:
            raise ValidationError("Image saving failed. Please try again.")

        return image

# Formset for handling multiple product images
ProductImageFormSet = forms.modelformset_factory(
    ProductImage, 
    form=ProductImageForm, 
    extra=4,  # Adjust this for multiple images
    can_delete=True  # Allow the option to delete images
)
