from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from products.models import Product, ProductVariant
# Create your models here.
class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"Cart of {self.user.username}"
    def get_total_price(self):
        return sum(item.quantity * item.variant.price for item in self.cartitem_set.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'variant')  # Ensure unique items per variant in each cart

    def total_price(self):
        return self.variant.price * self.quantity

    def __str__(self):
        return f"{self.variant} ({self.quantity}) in Cart"


class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, related_name='wishlists')
    variants = models.ManyToManyField(ProductVariant, related_name='wishlisted_by')

    def __str__(self):
        return f"{self.user.username}'s Wishlist"
