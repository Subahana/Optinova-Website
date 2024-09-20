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
    cancelled_at = models.DateTimeField(null=True, blank=True)

    def cancel_order(self):
        """Cancel the order and revert stock."""
        if not self.is_cancelled:
            self.is_cancelled = True
            self.cancelled_at = timezone.now()
            for item in self.items.all():  # Use 'items' as specified in the related_name
                item.variant.increase_stock(item.quantity)  # Revert stock
            self.status = 'Cancelled'
            self.save()



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