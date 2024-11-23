from django.conf import settings
from django.db import models

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return f"Wallet of {self.user.username} - Balance: {self.balance}"
   
class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    wallet = models.ForeignKey('Wallet', on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Update the wallet balance on transaction save
        if self.pk is None:  # Only update on creation
            if self.transaction_type == 'credit':
                self.wallet.balance += self.amount
            elif self.transaction_type == 'debit':
                self.wallet.balance -= self.amount
            self.wallet.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.amount} for {self.description}"
