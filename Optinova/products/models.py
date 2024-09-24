from django.db import models
from PIL import Image
from django.core.exceptions import ValidationError
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(default='')
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    def get_main_variant(self):
        # Fetch the main variant (assuming you have a related model `Variant`)
        return self.variants.filter(is_main_variant=True).first()
    
    @property
    def main_variant(self):
        return self.variants.filter(is_main_variant=True).first()

    @property
    def price(self):
        main_variant = self.main_variant
        return main_variant.price if main_variant else self.base_price

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    is_main_variant = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['product', 'color'], name='unique_product_color')
        ]

    def __str__(self):
        return f'{self.product.name} - {self.color}'

    @property
    def is_sold_out(self):
        return self.stock <= 0

    def save(self, *args, **kwargs):
        if self.is_main_variant:
            # Ensure only one main variant exists
            ProductVariant.objects.filter(product=self.product, is_main_variant=True).update(is_main_variant=False)
        super().save(*args, **kwargs)

    def decrease_stock(self, quantity):
        if self.stock >= quantity:
            self.stock -= quantity
            self.save()
        else:
            raise ValueError('Not enough stock available')

    def increase_stock(self, quantity):
        self.stock += quantity
        self.save()

    def clean(self):
        if self.stock < 0:
            raise ValidationError('Stock cannot be negative.')


class ProductImage(models.Model):
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/', max_length=500)

    def __str__(self):
        return f'Image for {self.variant.product.name} ({self.variant.color})'

    def save(self, *args, **kwargs):
        # Call the original save method
        super().save(*args, **kwargs)

        # Resize the image only if necessary
        self.resize_image()

    def resize_image(self):
        try:
            # Open the image
            img = Image.open(self.image)

            # Set output size
            output_size = (800, 800)

            # Only resize if the image is larger than the output size
            if img.height > output_size[1] or img.width > output_size[0]:
                # Create a BytesIO stream for the resized image
                img.thumbnail(output_size)
                img_format = img.format

                output = BytesIO()
                img.save(output, format=img_format)
                output.seek(0)

                # Create a new InMemoryUploadedFile
                self.image = InMemoryUploadedFile(
                    output, 'ImageField', self.image.name, 
                    img_format.lower(), sys.getsizeof(output), None
                )

                # Save the resized image
                super().save()

        except Exception as e:
            print(f"Error resizing the image: {e}")
