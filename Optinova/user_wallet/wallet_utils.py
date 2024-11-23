from .models import Wallet, WalletTransaction

def ensure_wallet_exists(user):
    """
    Ensures the given user has a wallet. Creates one if it does not exist.
    """
    wallet, created = Wallet.objects.get_or_create(user=user)
    return wallet


def credit_wallet(user, amount, description=""):
    """
    Credits the user's wallet with the specified amount and logs the transaction.
    """
    if amount <= 0:
        raise ValueError("Credit amount must be positive.")
    
    wallet = ensure_wallet_exists(user)
    wallet.balance += amount
    wallet.save()

    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type='refund',
        amount=amount,
        description=description
    )
    return wallet.balance

def debit_wallet(user, amount, description):
    """
    Deducts the specified amount from the user's wallet.
    """
    if user.wallet_balance < amount:
        raise Exception("Insufficient balance in wallet")

    user.wallet_balance -= amount
    user.save()

    # Create a WalletTransaction record for the debit
    WalletTransaction.objects.create(
        user=user,
        amount=-amount,
        description=description,
        transaction_type='debit'
    )

    return user.wallet_balance


def process_refund_to_wallet(order):
    """
    Process refund for a returned order, crediting the amount back to the user's wallet.
    """
    total_refund_amount = sum(item.total_price() for item in order.items.all())
    description = f"Refund for Order #{order.order_id}"
    credit_wallet(user=order.user, amount=total_refund_amount, description=description)
