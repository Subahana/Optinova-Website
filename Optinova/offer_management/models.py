from django.db import models
from django.core.exceptions import ValidationError
from products.models import Category
from django.utils import timezone

class CategoryOffer(models.Model):
    category = models.ForeignKey(Category, related_name='offers', on_delete=models.CASCADE)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Discount Percentage")
    start_date = models.DateField(null=True, blank=True, verbose_name="Start Date")
    end_date = models.DateField(null=True, blank=True, verbose_name="End Date")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    def clean(self):
        # Check if both dates are provided before comparing
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError("End date must be after the start date.")
        elif not self.start_date:
            raise ValidationError("Start date is required.")
        elif not self.end_date:
            raise ValidationError("End date is required.")

    def is_offer_active(self):
        """Check if the offer is currently active based on dates."""
        now = timezone.now().date()
        return self.is_active and self.start_date <= now <= self.end_date

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.category} - {self.discount_percent}% from {self.start_date} to {self.end_date} ({status})"
