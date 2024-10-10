from django.db import models
from django.utils import timezone
from products.models import Product  

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
        return self.active and self.valid_from <= now <= self.valid_to

    def __str__(self):
        return self.code
