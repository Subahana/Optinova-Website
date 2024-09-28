from django.conf import settings
from django.db import models
from user_profile.models import Address
from django.utils import timezone
from products.models import ProductVariant

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)  # Add address field
    payment_method = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    is_cancelled = models.BooleanField(default=False)
    canceled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='canceled_orders')
    cancelled_at = models.DateTimeField(null=True, blank=True)  
    cancellation_reason = models.CharField(max_length=100, null=True, blank=True)
    is_returned = models.BooleanField(default=False)

    def cancel_order(self, reason=None):
        """Cancel the order and revert stock."""
        if not self.is_cancelled:
            self.is_cancelled = True
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason or 'Cancelled by User'  # Set reason
            for item in self.items.all():
                item.variant.increase_stock(item.quantity)  # Revert stock
            self.status = 'Cancelled'
            self.save()

    def return_order(self):
        if not self.is_returned and self.status == 'Delivered':
            self.is_returned = True
            self.save()
    def total_amount(self):
        return sum(item.total_price() for item in self.items.all())
    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, related_name='order_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Add price field

    def save(self, *args, **kwargs):
        """Reduce stock when the item is added to an order."""
        if not self.pk:  # Item is being created
            self.variant.decrease_stock(self.quantity)
        super().save(*args, **kwargs)

    def total_price(self):
        return self.variant.price * self.quantity
    
    