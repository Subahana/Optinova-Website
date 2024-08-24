from django.db.models.signals import post_save
from django.conf import settings
from django.dispatch import receiver
from .models import OtpToken
from django.core.mail import send_mail
from django.utils import timezone

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_token(sender, instance, created, **kwargs):
    if created:
        if instance.is_superuser:
            return  # Do not create an OTP for superusers

        # Create OTP token
        otp = OtpToken.objects.create(
            user=instance, 
            otp_expires_at=timezone.now() + timezone.timedelta(minutes=1)
        )
        
        # Deactivate user until they verify their email
        instance.is_active = False
        instance.save()

        # Ensure the OTP token was created successfully
        if otp and otp.otp_code:
            subject = "Email Verification"
            message = f"""
                Hi {instance.username}, here is your OTP {otp.otp_code}. 
                It expires in 1 minutes. Use the URL below to verify your email:
                http://127.0.0.1:8000/email_verify/{instance.username}
            """
            sender_email = settings.DEFAULT_FROM_EMAIL
            receiver_email = [instance.email]
            
            # Send email
            send_mail(
                subject,
                message,
                sender_email,
                receiver_email,
                fail_silently=False,
            )
        else:
            print(f"Failed to create OTP for user {instance.username}")
    else:
        print(f"User {instance.username} was updated, not created.")

