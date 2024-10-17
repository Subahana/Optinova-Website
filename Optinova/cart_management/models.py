from django.db import models
from django.conf import settings
from products.models import Product, ProductVariant
from coupon_management.models import Coupon 


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL) 

    def __str__(self):
        return f"Cart of {self.user.username}"

    def get_total_price(self):
 
        original_total = self.get_original_total()
        
        if self.coupon and self.coupon.is_valid():
            discount = self.coupon.get_discount_amount(original_total) 
            total = original_total - discount
        else:
            total = original_total
        
        return total

    def get_discount(self):

        if self.coupon and self.coupon.is_valid():
            return self.coupon.get_discount_amount(self.get_original_total())
        return 0

    def get_original_total(self):

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
