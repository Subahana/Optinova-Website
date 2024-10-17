from django.conf import settings
from django.db import models
from django.utils import timezone
from user_profile.models import Address
from products.models import ProductVariant
from coupon_management.models import Coupon  

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('razorpay', 'Online Payment (Razorpay)'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    is_cancelled = models.BooleanField(default=False)
    canceled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='canceled_orders')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=100, null=True, blank=True)
    is_returned = models.BooleanField(default=False)
    payment_status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed')], default='PENDING')
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)

    def total_amount(self):
        """Calculate the total amount before discount."""
        total = sum(item.total_price() for item in self.items.all())
        return total



class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, related_name='order_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.price = self.variant.price
            self.variant.decrease_stock(self.quantity)
        super().save(*args, **kwargs)

    def total_price(self):
        return self.price * self.quantity
