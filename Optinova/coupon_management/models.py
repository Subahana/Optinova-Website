from django.db import models
from django.utils import timezone
from products.models import Product  # Assuming your coupons are related to products

class Coupon(models.Model):
    COUPON_TYPES = (
        ('percentage', 'Percentage Discount'),
        ('fixed', 'Fixed Amount Discount'),
    )
    
    code = models.CharField(max_length=50, unique=True)
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPES, default='percentage')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    def is_valid(self):
        now = timezone.now()
        print("Current time:", now)
        print("Valid from:", self.valid_from)
        print("Valid to:", self.valid_to)
        print("Active status:", self.active)
        return self.active and (self.valid_from <= now <= self.valid_to)

    def get_discount_amount(self, total_amount):
        if self.coupon_type == 'percentage' and self.discount_percentage:
            return total_amount * (self.discount_percentage / 100)
        elif self.coupon_type == 'fixed' and self.discount_amount:
            return min(self.discount_amount, total_amount)  
        return 0

    def __str__(self):
        return self.code

