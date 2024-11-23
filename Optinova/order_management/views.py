from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from django.middleware.csrf import get_token
from django.http import JsonResponse, HttpResponseForbidden
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Order, OrderItem ,PaymentDetails, PaymentStatus, OrderStatus
from user_profile.models import Address
from cart_management.models import Cart, CartItem
from .forms import OrderForm
import razorpay
from razorpay import Client
import logging
from urllib.parse import parse_qs
from user_wallet.models import WalletTransaction
from user_wallet.wallet_utils import debit_wallet ,credit_wallet ,process_refund_to_wallet
import uuid
from django.contrib.auth import login, get_backends


logger = logging.getLogger(__name__)


def generate_unique_order_id():
    """
    Generate a unique order ID using UUID4. Ensures no conflicts in the database.
    """
    order_id = str(uuid.uuid4())  # Generate a random UUID
    while Order.objects.filter(order_id=order_id).exists():  # Check for uniqueness
        order_id = str(uuid.uuid4())  # Regenerate if it already exists
    return order_id

razorpay_client = Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))


@login_required(login_url='accounts:user_login_view')
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    total_price = cart.final_price  # Use calculate_final_total method

    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)

        if form.is_valid():
            # Get or create address
            address_id = form.cleaned_data.get('address')
            if address_id == 'add_new':
                address = Address.objects.create(
                    user=request.user,
                    street=form.cleaned_data.get('new_street'),
                    city=form.cleaned_data.get('new_city'),
                    state=form.cleaned_data.get('new_state'),
                    pin_code=form.cleaned_data.get('new_pin_code'),
                    is_default=True
                )
            else:
                address = get_object_or_404(Address, id=address_id)

            payment_method = form.cleaned_data['payment_method']
            cart_items = CartItem.objects.filter(cart=cart)

            if not cart_items.exists():
                messages.error(request, "Your cart is empty.")
                return redirect('cart_detail')

            # Handle wallet payment
            if payment_method.lower() == 'wallet':
                try:
                    # Check wallet balance
                    wallet = ensure_wallet_exists(request.user)

                    if wallet.balance >= total_price:
                        # Deduct amount and create order
                        credit_wallet(request.user, -total_price, "Order Payment")  # Deduct from wallet

                        # Create PaymentDetails object
                        payment_details = PaymentDetails.objects.create(
                            payment_method="Wallet",
                            payment_status=PaymentStatus.objects.get(status="Completed")
                        )

                        # Create order after wallet deduction
                        order = Order.objects.create(
                            user=request.user,
                            address=address,
                            payment_details=payment_details,
                            order_id=generate_unique_order_id() , # Ensure unique order_id
                            final_price=total_price  # Store the final price

                        )

                        # Add cart items to the order
                        for item in cart_items:
                            OrderItem.objects.create(
                                order=order,
                                variant=item.variant,
                                quantity=item.quantity,
                                price=item.variant.price
                            )

                        # Remove cart items after successful payment
                        cart_items.delete()

                        messages.success(request, "Order placed successfully using wallet!")
                        return redirect('cod_order_success', order_id=order.id)

                    else:
                        messages.error(request, "Insufficient wallet balance. Please try another payment method.")
                        return redirect('checkout')

                except Exception as e:
                    messages.error(request, f"Error processing wallet payment: {str(e)}")
                    return redirect('cart_detail')

            # Handle Razorpay payment
            elif payment_method.lower() == 'razorpay':
                try:
                    razorpay_client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))

                    # Razorpay order creation
                    razorpay_order = razorpay_client.order.create({
                        "amount": int(total_price * 100),  # Convert Decimal to integer (paise)
                        "currency": "INR",
                        "payment_capture": 1
                    })

                    # Create PaymentDetails object
                    payment_details = PaymentDetails.objects.create(
                        payment_method="Razorpay",
                        payment_status=PaymentStatus.objects.get(status="Pending"),
                        razorpay_order_id=razorpay_order['id']
                    )

                    # Create order
                    order = Order.objects.create(
                        user=request.user,
                        address=address,
                        payment_details=payment_details,
                        order_id=generate_unique_order_id() , # Ensure unique order_id
                        final_price=total_price  # Store the final price

                    )

                    # Add order ID to session for verification
                    order.razorpay_order_id = razorpay_order['id']
                    order.save()

                    # Redirect to Razorpay payment page
                    return render(request, 'checkout/razorpay_payment.html', {
                        'order': order,
                        'razorpay_order_id': razorpay_order['id'],
                        'razorpay_key': settings.RAZOR_PAY_KEY_ID,
                        'total_price': total_price * 100,
                        'user_email': request.user.email,
                        'user_name': request.user.get_full_name(),
                        'csrf_token': get_token(request),
                    })

                except razorpay.errors.BadRequestError as e:
                    logger.error(f"Failed to create Razorpay order: {str(e)}")
                    messages.error(request, "Failed to create Razorpay order. Please try again.")
                    return redirect('checkout')
                except Exception as e:
                    logger.error(f"An unexpected error occurred: {str(e)}")
                    messages.error(request, "An unexpected error occurred. Please try again.")
                    return redirect('checkout')

            # Handle COD payment
            elif payment_method.lower() == 'cod':
                # Create PaymentDetails object
                payment_details = PaymentDetails.objects.create(
                    payment_method="COD",
                    payment_status=PaymentStatus.objects.get(status="Pending")
                )

                # Create order
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    payment_details=payment_details,
                    order_id=generate_unique_order_id() , # Ensure unique order_id
                    final_price=total_price  # Store the final price

                )

                # Add cart items to the order
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        variant=item.variant,
                        quantity=item.quantity,
                        price=item.variant.price
                    )

                # Remove cart items after order creation
                cart_items.delete()

                messages.success(request, "Order placed successfully with Cash on Delivery.")
                return redirect('cod_order_success', order_id=order.id)

    else:
        form = OrderForm(user=request.user)

    return render(request, 'checkout/checkout.html', {
        'form': form,
        'addresses': addresses,
        'cart_items': CartItem.objects.filter(cart=cart),
        'total_price': total_price,
        'csrf_token': get_token(request),
    })


@method_decorator(csrf_exempt, name='dispatch')
class VerifyRazorpayPayment(View):
    def post(self, request, order_id):  # Accept order_id as URL parameter
        
        print(f"Received payment callback for order_id: {order_id}")  # Log order_id
        decoded_body = request.body.decode('utf-8')
        print(f"Decoded body: {decoded_body}")  # Log the entire body
        data = parse_qs(decoded_body)
        data = {k: v[0] for k, v in data.items()}

        payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        signature = data.get('razorpay_signature')

        # Retrieve PaymentDetails
        payment_details = get_object_or_404(PaymentDetails, razorpay_order_id=razorpay_order_id)

        if not all([payment_id, razorpay_order_id, signature]):
            return JsonResponse({'error': 'Missing payment ID, order ID, or signature'}, status=400)

        razorpay_client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))

        try:
            # Verify the Razorpay payment signature
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })

            # Retrieve the associated Order
            order = get_object_or_404(Order, id=order_id)

            # Set order status to 'Processing'
            try:
                processing_status = OrderStatus.objects.get(status='Processing')
            except OrderStatus.DoesNotExist:
                logger.error("OrderStatus with 'Processing' status not found.")
                return JsonResponse({'error': 'Processing status not found'}, status=500)

            try:
                completed_payment_status = PaymentStatus.objects.get(status='Completed')
            except PaymentStatus.DoesNotExist:
                logger.error("PaymentStatus with 'Completed' status not found.")
                return JsonResponse({'error': 'Completed payment status not found'}, status=500)

            # Update order and payment details
            order.status = processing_status
            order.payment_details.payment_status = completed_payment_status
            order.payment_details.razorpay_payment_id = payment_id
            order.payment_details.save()
            order.save()
            print("after successfull verification",order_id)
            # Clear user's cart items
            CartItem.objects.filter(cart__user=order.user).delete()

            return redirect('razorpay_order_success',order_id=order_id)

        except razorpay.errors.SignatureVerificationError:
            logger.error("Payment verification failed due to signature mismatch.")
            return JsonResponse({'error': 'Signature verification failed'}, status=400)

        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            return JsonResponse({'error': 'An error occurred while processing payment'}, status=500)

@login_required(login_url='accounts:user_login_view')
def razorpay_order_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    # Fetch the associated user
    user = order.user
    print(user)
    # Log in the user
    if user.is_active:
        backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user, backend=backend)

    # Calculate the total price using the `total_amount` method
    total_price = order.total_amount()

    # Set the order status to 'Processing'
    processing_status = OrderStatus.objects.get(status="Processing")
    order.status = processing_status
    order.payment_details.payment_status = PaymentStatus.objects.get(status="Paid")
    order.payment_details.save()
    order.payment_date = timezone.now()
    order.save()

    # Clear the user's cart
    CartItem.objects.filter(cart__user=user).delete()

    # Render the success page
    return render(request, 'checkout/razorpay_order_success.html', {
        'order': order,
        'total_price': total_price,
        'payment_status': "Paid via Razorpay",
    })



def order_failure(request, razorpay_order_id):
    # Assuming you fetch the order details beforehand
    order = get_object_or_404(Order, razorpay_order_id=razorpay_order_id, user=request.user)

    # Mark payment as failed
    order.payment_status = 'Failed'
    order.save()

    # Redirect to the order failure page where users can retry payment
    return redirect(reverse('checkout:complete_payment', args=[order.id]))


@login_required(login_url='accounts:user_login_view')
def complete_payment(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        print(f"Order found: {order}")

        if not order.payment_details or order.payment_details.payment_status.status != 'Completed':
            total_price = request.session.get('total_price', 0)
            print(f"Total price from session: {total_price}")

            if request.method == 'POST':
                payment_option = request.POST.get('payment_option')
                print(f"Selected payment option: {payment_option}")

                if payment_option == 'wallet':
                    wallet_balance = request.user.wallet.balance
                    print(f"Wallet balance: {wallet_balance}, Total price: {total_price}")

                    if wallet_balance >= total_price:
                        request.user.wallet.balance -= total_price
                        request.user.wallet.save()
                        payment_status = PaymentStatus.objects.get_or_create(status='Completed')[0]
                        payment_details = PaymentDetails.objects.create(
                            payment_method='wallet',
                            payment_status=payment_status,
                        )
                        order.payment_details = payment_details
                        order.save()
                        return render(request, 'checkout/payment_success.html', {
                            'order': order,
                            'message': "Payment completed using wallet."
                        })
                    else:
                        return render(request, 'checkout/complete_payment.html', {
                            'order': order,
                            'total_price': total_price * 100,
                            'insufficient_balance': True
                        })

                elif payment_option == 'razorpay':
                    try:
                        razorpay_client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))
                        razorpay_order = razorpay_client.order.create(data={
                            "amount": int(total_price * 100),  # Convert Decimal to integer (paise)
                            'currency': 'INR',
                            'payment_capture': '1',
                        })
                        print(f"Razorpay Order Created: {razorpay_order}")

                        razorpay_order_id = razorpay_order['id']
                        order.razorpay_order_id = razorpay_order_id
                        order.save()

                        payment_status = PaymentStatus.objects.get_or_create(status='Pending')[0]
                        payment_details, _ = PaymentDetails.objects.get_or_create(
                            razorpay_order_id=razorpay_order_id,
                            defaults={
                                'payment_method': 'razorpay',
                                'payment_status': payment_status,
                            }
                        )
                        order.payment_details = payment_details
                        order.save()

                        request.session['razorpay_order_id'] = razorpay_order_id
                        return render(request, 'checkout/complete_payment.html', {
                            'order': order,
                            'razorpay_order_id': razorpay_order_id,
                            'razorpay_key': settings.RAZOR_PAY_KEY_ID,
                            'total_price': total_price * 100,
                            'user_email': request.user.email,
                            'user_name': request.user.get_full_name(),
                            'csrf_token': get_token(request),
                        })

                    except razorpay.errors.RazorpayError as e:
                        logger.error(f"Razorpay API error: {e}")
                        print(f"Razorpay API error: {e}")
                        return render(request, 'checkout/payment_error.html', {
                            'error_message': "There was an issue with the payment gateway. Please try again later."
                        })

            return render(request, 'checkout/complete_payment.html', {
                'order': order,
                'total_price': total_price * 100,
            })

        else:
            return render(request, 'checkout/payment_error.html', {
                'error_message': "This order has already been paid for."
            })

    except Order.DoesNotExist:
        print("Order not found")
        return render(request, 'checkout/payment_error.html', {
            'error_message': "Order not found."
        })

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        print(f"Unexpected error: {str(e)}")
        return render(request, 'checkout/payment_error.html', {
            'error_message': "An unexpected error occurred. Please try again later."
        })



@login_required(login_url='accounts:user_login_view')
def cod_order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.order_date = timezone.now()
    order.save()

    CartItem.objects.filter(cart__user=request.user).delete()

    return render(request, 'checkout/cod_order_success.html', {
        'order': order,
        'total_price':request.session.get('total_price', None),
        'payment_status': "Cash on Delivery",
    })


def list_orders(request):
    orders = Order.objects.filter(items__variant__is_active=True).distinct()

    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(user__username__icontains=search_query)

    status_filter = request.GET.get('status_filter', '')
    if status_filter:
        orders = orders.filter(status=status_filter)

    sort_option = request.GET.get('sort', '')
    if sort_option == 'date_asc':
        orders = orders.order_by('created_at')
    elif sort_option == 'date_desc':
        orders = orders.order_by('-created_at')
    elif sort_option == 'status_asc':
        orders = orders.order_by('status')
    elif sort_option == 'status_desc':
        orders = orders.order_by('-status')

    return render(request, 'checkout/list_orders.html', {'orders': orders})


def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Prevent updating status if the order is cancelled by the user
    if order.status.status == 'Cancelled by User':
        messages.error(request, 'This order cannot be updated as it has been cancelled by the user.')
        return redirect('list_orders')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status:
            # Get the OrderStatus instance corresponding to the new status
            status_instance = get_object_or_404(OrderStatus, status=new_status)
            order.status = status_instance  # Assign the status instance
            if new_status == 'Delivered':
                order.payment_status = 'Completed'
            order.save()
            messages.success(request, 'Order status updated successfully.')

    return redirect('list_orders')



def cancel_order_request(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status.status.lower() in ["pending", "processing"]:
        if request.method == "POST":
            cancellation_reason = request.POST.get("cancellation_reason")

            # Set the cancellation details
            order.is_cancelled = True
            order.canceled_by = request.user
            order.cancelled_at = timezone.now()
            order.cancellation_reason = cancellation_reason

            # Update the order status to 'Cancelled'
            cancelled_status, _ = OrderStatus.objects.get_or_create(status="Cancelled")
            order.status = cancelled_status

            # Refund to wallet if payment is completed
            if order.payment_details and order.payment_details.payment_status.status == "Completed":
                try:
                    refund_amount = order.total_amount()  # Assuming `order.total_amount()` gives the total amount
                    description = f"Refund for Order #{order.id}"
                    credit_wallet(user=order.user, amount=refund_amount, description=description)
                    messages.success(request, f"Refund of {refund_amount} has been credited to your wallet.")
                except Exception as e:
                    messages.error(request, f"Refund failed: {str(e)}")

            order.save()

            messages.success(request, "Your order has been successfully cancelled.")
            return redirect('my_orders')
        else:
            messages.error(request, "Cancellation reason is required.")
            return redirect('order_details', order_id=order.id)
    else:
        messages.error(request, "You cannot cancel this order at this stage.")
        return redirect('order_details', order_id=order.id)


def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status.status != "Delivered":
        messages.error(request, "Only delivered orders can be returned.")
        return redirect('order_details', order_id=order.id)

    if request.method == "POST":
        return_reason = request.POST.get('return_reason')
        if return_reason:
            order.is_returned = True
            order.return_reason = return_reason

            # Refund to wallet if payment is completed
            if order.payment_details and order.payment_details.payment_status.status == "Completed":
                try:
                    process_refund_to_wallet(order)
                    messages.success(request, "Refund has been credited to your wallet.")
                except Exception as e:
                    messages.error(request, f"Refund failed: {str(e)}")

            order.save()

            messages.success(request, "Your order has been successfully returned.")
            return redirect('order_details', order_id=order.id)
        else:
            messages.error(request, "Please provide a reason for the return.")
            return redirect('order_details', order_id=order.id)

    return redirect('order_details', order_id=order.id)
