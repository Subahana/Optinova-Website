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
from user_wallet.wallet_utils import debit_wallet ,credit_wallet ,process_refund_to_wallet,ensure_wallet_exists
import uuid
from django.contrib.auth import login, get_backends
from django.core.paginator import Paginator
from decimal import Decimal


logger = logging.getLogger(__name__)



razorpay_client = Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))


@login_required(login_url='accounts:user_login_view')
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    total_price = cart.final_price

    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)

        if form.is_valid():
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

            # Determine initial payment status
            if payment_method.lower() == "cod":
                payment_status_value = "Pending"
            elif payment_method.lower() in ["razorpay", "wallet"]:
                payment_status_value = "Completed"  # Set completed if payment is successful
            else:
                payment_status_value = "Pending"  # Default for unknown methods

            # Redirect based on payment method
            if payment_method.lower() == "cod":
                payment_status, _ = PaymentStatus.objects.get_or_create(
                status=payment_status_value)

                # Create PaymentDetails object
                payment_details = PaymentDetails.objects.create(
                    payment_method=payment_method.capitalize(),
                    payment_status=payment_status
                )

                # Create Order object
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    payment_details=payment_details,
                    final_price=total_price
                )

                # Add cart items to the order
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        variant=item.variant,
                        quantity=item.quantity,
                        price=item.variant.price
                    )

                cart_items.delete()
                messages.success(request, "Order placed successfully with Cash on Delivery.")
                return redirect('cod_order_success', order_id=order.id)
            elif payment_method.lower() == "wallet":
                if ensure_wallet_exists(request.user).balance >= total_price:
                    debit_wallet(request.user, total_price, "Order Payment via Wallet")
                    payment_status, _ = PaymentStatus.objects.get_or_create(
                    status=payment_status_value)

                    # Create PaymentDetails object
                    payment_details = PaymentDetails.objects.create(
                        payment_method=payment_method.capitalize(),
                        payment_status=payment_status
                    )

                    # Create Order object
                    order = Order.objects.create(
                        user=request.user,
                        address=address,
                        payment_details=payment_details,
                        final_price=total_price
                    )

                    # Add cart items to the order
                    for item in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            variant=item.variant,
                            quantity=item.quantity,
                            price=item.variant.price
                        )

                    cart_items.delete()
                    messages.success(request, "Order placed successfully using Wallet!")
                    return redirect('cod_order_success', order_id=order.id)
                else:
                    messages.error(request, "Insufficient wallet balance.")
                    return redirect('checkout')
            elif payment_method.lower() == "razorpay":
                payment_status, _ = PaymentStatus.objects.get_or_create(status="Pending")

                # Create PaymentDetails object
                payment_details = PaymentDetails.objects.create(
                    payment_method=payment_method.capitalize(),
                    payment_status=payment_status
                )

                # Create Order object
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    payment_details=payment_details,
                    final_price=total_price
                )
                razorpay_client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))
                razorpay_order = razorpay_client.order.create({
                    "amount": int(total_price * 100),
                    "currency": "INR",
                    "payment_capture": 1
                })
                
                order.razorpay_order_id = razorpay_order['id']
                order.save()

                cart_items.delete()
                return render(request, 'checkout/razorpay_payment.html', {
                    'order': order,
                    'razorpay_order_id': razorpay_order['id'],
                    'razorpay_key': settings.RAZOR_PAY_KEY_ID,
                    'total_price': total_price * 100,
                    'user_email': request.user.email,
                    'user_name': request.user.get_full_name(),
                    'csrf_token': get_token(request),
                })
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
        payment_details = get_object_or_404(PaymentDetails, order__id=order_id)

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
                processing_status = OrderStatus.objects.get(status='Pending')
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
            total_price = request.session.get('total_price_order', 0)
            print(f"Total price from session: {total_price}")

            if request.method == 'POST':
                payment_option = request.POST.get('payment_option')
                print(f"Selected payment option: {payment_option}")

                if payment_option == 'wallet':
                    wallet_balance = request.user.wallet.balance
                    print(f"Wallet balance: {wallet_balance}, Total price: {total_price}")

                    if wallet_balance >= total_price:
                        request.user.wallet.balance -= Decimal(str(total_price))
                        request.user.wallet.save()
                        payment_status = PaymentStatus.objects.get_or_create(status='Completed')[0]
                        payment_details = PaymentDetails.objects.create(
                            payment_method='wallet',
                            payment_status=payment_status,
                        )
                        order.payment_details = payment_details
                        order.save()
                        return render(request, 'checkout/cod_order_success.html', {
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
                        order.razorpay_order_id = razorpay_order['id']
                        order.save()

                        request.session['razorpay_order_id'] = razorpay_order_id
                        return render(request, 'checkout/complete_payment.html', {
                            'order': order,
                            'razorpay_order_id': razorpay_order['id'],
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
    final_price = order.final_price  # Assuming final_price is a field in your Order model

    return render(request, 'checkout/cod_order_success.html', {
        'order': order,
        'total_price':final_price,
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

    # Pagination
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'checkout/list_orders.html', {'orders': orders,'page_obj': page_obj})



def update_order_status(request, order_id):
    """
    Update the status of an order to 'Delivered'.
    Only accessible to staff members.
    """
    order = get_object_or_404(Order, id=order_id)
    
    try:
        delivered_status, _ = OrderStatus.objects.get_or_create(status="Delivered")
        order.status = delivered_status
        order.save()
        messages.success(request, f"Order #{order.order_id} status updated to 'Delivered'.")
    except Exception as e:
        messages.error(request, f"Failed to update order status: {str(e)}")
    
    return redirect("list_orders")




def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    print(order)
    # Debugging: Log the current order status
    logger.debug(f"Order ID: {order.id}, Current Status: {order.status.status}")

    # Ensure cancellation is allowed based on status
    if order.status.status.lower() in ["pending", "processing"] and \
       (not order.payment_details or order.payment_details.payment_status.status.lower() == "pending"):
        print(order)
        if request.method == "POST":
            cancellation_reason = request.POST.get("cancel_reason")
            print(cancellation_reason)
            logger.debug(f"Cancellation Reason: {cancellation_reason}")  # Log the cancellation reason

            if not cancellation_reason:
                messages.error(request, "Cancellation reason is required.")
                return redirect('order_details', order_id=order.id)

            # Proceed with cancellation
            try:
                order.is_cancelled = True
                order.canceled_by = request.user
                order.cancelled_at = timezone.now()
                order.cancellation_reason = cancellation_reason

                # Update order status to 'Cancelled'
                cancelled_status, _ = OrderStatus.objects.get_or_create(status="Cancelled")
                order.status = cancelled_status

                # Debugging: Log order details after changes
                logger.debug(f"Order Updated - ID: {order.id}, Status: {order.status.status}, is_cancelled: {order.is_cancelled}")

                # Save order
                order.save()

                messages.success(request, "Your order has been successfully canceled.")
                return redirect('my_orders')

            except Exception as e:
                logger.error(f"Error saving order cancellation: {e}")
                messages.error(request, "There was an error processing the cancellation.")
                return redirect('order_details', order_id=order.id)

    else:
        messages.error(request, "You cannot cancel this order at this stage.")
        return redirect('order_details', order_id=order.id)

def cancel_order_with_refund(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Debugging: Log current status and payment status
    logger.debug(f"Order ID: {order.id}, Current Status: {order.status.status}, Payment Status: {order.payment_details.payment_status.status if order.payment_details else 'No Payment Details'}")

    if order.status.status.lower() in ["pending", "processing"] and order.payment_details and order.payment_details.payment_status.status.lower() == "completed":
        if request.method == "POST":
            cancellation_reason = request.POST.get("cancel_reason")
            logger.debug(f"Cancellation Reason: {cancellation_reason}")

            if not cancellation_reason:
                messages.error(request, "Cancellation reason is required.")
                return redirect('order_details', order_id=order.id)

            try:
                # Update order details
                order.is_cancelled = True
                order.canceled_by = request.user
                order.cancelled_at = timezone.now()
                order.cancellation_reason = cancellation_reason
                cancelled_status, _ = OrderStatus.objects.get_or_create(status="Cancelled")
                order.status = cancelled_status

                # Log the order cancellation
                logger.debug(f"Order Updated - ID: {order.id}, Status: {order.status.status}, is_cancelled: {order.is_cancelled}")

                # Update the payment status to 'Refund'
                if order.payment_details:
                    returned_status, _ = PaymentStatus.objects.get_or_create(status='Refund')
                    order.payment_details.payment_status = returned_status
                    order.payment_details.save()
                # Save the updated order
                order.save()

                messages.success(request, "Your order has been successfully canceled with a refund.")
                return redirect('my_orders')

            except Exception as e:
                logger.error(f"Error processing refund: {e}")
                messages.error(request, f"Refund failed: {str(e)}")
                return redirect('order_details', order_id=order.id)
    else:
        messages.error(request, "You cannot cancel this order at this stage.")
        return redirect('order_details', order_id=order.id)

def return_order_with_refund(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Debugging: Log the current order status and payment status
    logger.debug(f"Order ID: {order.id}, Current Status: {order.status.status}, Payment Status: {order.payment_details.payment_status.status if order.payment_details else 'No Payment Details'}")

    # Ensure return is allowed based on order status
    if order.status.status.lower() == "delivered" and \
       order.payment_details and order.payment_details.payment_status.status.lower() == "completed":

        if request.method == "POST":
            return_reason = request.POST.get("return_reason")
            logger.debug(f"Return Reason: {return_reason}")  # Log the return reason

            if not return_reason:
                messages.error(request, "Return reason is required.")
                return redirect('order_details', order_id=order.id)

            # Proceed with return and refund in a transaction
            try:
                order.is_returned = True
                order.return_reason = return_reason
                order.returned_at = timezone.now()

                # Debugging: Log order details after return
                logger.debug(f"Order Updated - ID: {order.id}, is_returned: {order.is_returned}")

                # Process the refund to wallet (assuming this is a defined method)
                process_refund_to_wallet(order)

                # Save order
                order.save()

                messages.success(request, "Your order has been successfully returned with a refund.")
                return redirect('my_orders')

            except Exception as e:
                logger.error(f"Error processing return with refund: {e}")
                messages.error(request, f"Refund failed: {str(e)}")
                return redirect('order_details', order_id=order.id)

    else:
        messages.error(request, "You cannot return this order at this stage.")
        return redirect('order_details', order_id=order.id)

def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Debugging: Log the current order status
    logger.debug(f"Order ID: {order.id}, Current Status: {order.status.status}")

    if order.status.status.lower() == "delivered" and \
       (not order.payment_details or order.payment_details.payment_status.status.lower() == "pending"):

        if request.method == "POST":
            return_reason = request.POST.get("return_reason")
            logger.debug(f"Return Reason: {return_reason}")  # Log the return reason

            if not return_reason:
                messages.error(request, "Return reason is required.")
                return redirect('order_details', order_id=order.id)

            # Proceed with return
            try:
                order.is_returned = True
                order.return_reason = return_reason
                order.returned_at = timezone.now()

                # Debugging: Log order details after return
                logger.debug(f"Order Updated - ID: {order.id}, is_returned: {order.is_returned}")

                # Save order
                order.save()

                messages.success(request, "Your order has been successfully returned.")
                return redirect('my_orders')

            except Exception as e:
                logger.error(f"Error processing return: {e}")
                messages.error(request, "There was an error processing the return.")
                return redirect('order_details', order_id=order.id)

    else:
        messages.error(request, "You cannot return this order at this stage.")
        return redirect('order_details', order_id=order.id)
