from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, OrderStatus, PaymentDetails

@receiver(post_save, sender=Order)
def set_processing_status(sender, instance, created, **kwargs):
    """
    Signal to set order status to 'Processing' upon order creation:
    - For COD: Directly set the status to 'Processing' upon creation.
    - For Online Payments: Set the status to 'Processing' only if the payment is completed.
    """
    if created:
        if instance.payment_details.payment_method == "COD":
            # For COD, immediately set the status to 'Processing'
            processing_status, _ = OrderStatus.objects.get_or_create(status="Processing")
            instance.status = processing_status
            instance.save()
        elif instance.payment_details.payment_method in ["razorpay", "Wallet"]:
            # For online payments, ensure payment status is 'Completed' before setting 'Processing'
            if instance.payment_details.payment_status.status == "Completed":
                processing_status, _ = OrderStatus.objects.get_or_create(status="Processing")
                instance.status = processing_status
                instance.save()
