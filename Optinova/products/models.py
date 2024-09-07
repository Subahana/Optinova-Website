from django.db import models
from PIL import Image

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

    def __str__(self):
        return f'{self.product.name} - {self.color}'

    @property
    def is_sold_out(self):
        return self.stock <= 0

    def save(self, *args, **kwargs):
        if self.is_main_variant:
            ProductVariant.objects.filter(product=self.product, is_main_variant=True).update(is_main_variant=False)
        super().save(*args, **kwargs)

class ProductImage(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/', max_length=500)

    def __str__(self):
        return f'Image for {self.variant.product.name} ({self.variant.color})'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.resize_image()

    def resize_image(self):
        img = Image.open(self.image.path)
        output_size = (800, 800)
        if img.height > output_size[1] or img.width > output_size[0]:
            img.thumbnail(output_size)
            img.save(self.image.path)
