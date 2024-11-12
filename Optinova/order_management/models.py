from django.conf import settings
from django.db import models
from django.utils import timezone
from user_profile.models import Address
from products.models import ProductVariant
from coupon_management.models import Coupon
import uuid
# Constants for default status values
DEFAULT_ORDER_STATUS = "Pending"
DEFAULT_PAYMENT_STATUS = "Pending"

class OrderStatus(models.Model):
    status = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.status
    # To ensure a default status is set:
    def save(self, *args, **kwargs):
        if not self.id:  # Check if the instance has no ID (meaning it's new)
            # Default behavior if a new object is being created
            self.status = self.status or "Pending"  # Ensure a default value if not provided
        super().save(*args, **kwargs)

    @staticmethod
    def get_default_status():
        # Ensure the "Pending" status exists and return it
        return OrderStatus.objects.get_or_create(status=DEFAULT_ORDER_STATUS)[0].id

class PaymentStatus(models.Model):
    status = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.status

    @staticmethod
    def get_default_payment_status():
        # Ensure the "Pending" status exists and return it
        return PaymentStatus.objects.get_or_create(status=DEFAULT_PAYMENT_STATUS)[0].id

class PaymentDetails(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('razorpay', 'Online Payment (Razorpay)'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    payment_status = models.ForeignKey(
        PaymentStatus, on_delete=models.SET_NULL, null=True,
        default=PaymentStatus.get_default_payment_status
    )


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=20, editable=False)  
    payment_details = models.OneToOneField(PaymentDetails, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.ForeignKey(OrderStatus, on_delete=models.CASCADE, default=OrderStatus.get_default_status)  # Default set here
    is_cancelled = models.BooleanField(default=False)
    canceled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='canceled_orders')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=100, null=True, blank=True)
    is_returned = models.BooleanField(default=False)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=255, null=True, blank=True)  # Add this line to store Razorpay Order ID

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = self.generate_order_id()
        super().save(*args, **kwargs)


    def generate_order_id(self):
        """Generate a unique order ID in the format ORD202410001."""
        current_year = timezone.now().year
        last_order = Order.objects.filter(created_at__year=current_year).order_by('id').last()
        
        if last_order:
            last_id_number = int(last_order.order_id[-5:])  # Extract the last 5 digits
            new_id_number = last_id_number + 1
        else:
            new_id_number = 10001  # Start numbering from 10001 for the first order of the year

        return f"ORD{current_year}{new_id_number:05d}"
    
    def total_amount(self):
        """Calculate the total amount before discount."""
        return sum(item.total_price() for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, related_name='order_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.pk:
            # Set the price from the variant and decrease stock
            self.price = self.variant.price
            self.variant.decrease_stock(self.quantity)
        super().save(*args, **kwargs)

    def total_price(self):
        return self.price * self.quantity
