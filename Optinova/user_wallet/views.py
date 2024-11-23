from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from .wallet_utils import credit_wallet, debit_wallet, ensure_wallet_exists
from .models import WalletTransaction
from order_management.models import Order

@login_required(login_url='accounts:user_login_view')
def wallet(request):
    wallet = ensure_wallet_exists(request.user)  
    transactions = wallet.transactions.all().order_by('-date')  
    print(transactions,wallet)
    context = {
        'wallet': wallet,
        'transactions': transactions,
    }
    return render(request, 'wallet/wallet_display.html', context)

def add_funds(request):
    if request.method == 'POST':
        try:
            # Parse request data
            data = json.loads(request.body)
            user = request.user
            amount = int(data.get('amount')) * 100  # Convert to paise

            # Check if the user has a returned order with the requested refund amount
            returned_order = Order.objects.filter(
                user=user, 
                status='returned', 
                refund_amount=amount // 100,  # Convert back to rupees
                wallet_credited=False
            ).first()

            if not returned_order:
                return JsonResponse({
                    "success": False, 
                    "error": "No eligible returned order found for refund."
                })

            # Create Razorpay order
            client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))
            razorpay_order = client.order.create({
                "amount": amount,
                "currency": "INR",
                "payment_capture": 1
            })
            print("Order created successfully:", razorpay_order)

            # Update the returned order to mark the refund process initiated
            returned_order.wallet_credited = True
            returned_order.save()

            return JsonResponse({
                "success": True,
                "order_id": razorpay_order["id"],
                "amount": razorpay_order["amount"],
                "razorpay_key": settings.RAZOR_PAY_KEY_ID,  # Razorpay key
                "csrf_token": get_token(request),
            })
        except Exception as e:
            print("Error creating order:", str(e))
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request method."})


@login_required(login_url='accounts:user_login_view')
def wallet_payment(request):
    """
    Deduct funds from the wallet for a purchase.
    """
    if request.method == 'POST':
        amount = float(request.POST.get('amount', 0))
        try:
            new_balance = debit_wallet(request.user, amount, "Purchase made")
            return JsonResponse({"success": True, "new_balance": new_balance})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request method"})
 