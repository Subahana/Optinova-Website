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
import logging
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)

@login_required(login_url='accounts:user_login_view')
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    total_price = cart.calculate_final_total()  # Use calculate_final_total method

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

            # Create a PaymentDetails object
            payment_details = PaymentDetails.objects.create(
                payment_method=payment_method,
                payment_status=PaymentStatus.objects.get(id=PaymentStatus.get_default_payment_status())
            )
            print(payment_details)
            # Create the order
            order = Order.objects.create(
                user=request.user,
                address=address,
                payment_details=payment_details,  # Associate PaymentDetails with the order
            )
            print(order)
            # Fetch cart items
            cart_items = CartItem.objects.filter(cart=cart)
            if not cart_items.exists():
                messages.error(request, "Your cart is empty.")
                return redirect('cart_detail')

            # Add cart items to the order
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    quantity=item.quantity,
                    price=item.variant.price
                )

            total_price = int(cart.get_total_price() * 100)
            request.session['total_price'] = total_price
            print(request.session.get('total_price', 0))

            if total_price <= 0:
                messages.error(request, "Total price is invalid.")
                return redirect('cart_detail')

            if payment_method.lower() == 'razorpay':
                try:
                    razorpay_client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))

                    # Razorpay order creation
                    razorpay_order = razorpay_client.order.create({
                        "amount": total_price,
                        "currency": "INR",
                        "payment_capture": 1
                    })


                    order.razorpay_order_id = razorpay_order['id']
                    order.save()
                    print('yes order',order)

                    payment_details.razorpay_order_id = razorpay_order['id']  # Correctly assign to PaymentDetails
                    payment_details.save()
                    print('yes payment_details',payment_details)

                    return render(request, 'checkout/razorpay_payment.html', {
                        'order': order,
                        'razorpay_order_id': order.razorpay_order_id,
                        'razorpay_key': settings.RAZOR_PAY_KEY_ID,
                        'total_price': total_price *100, 
                        'user_email': request.user.email,
                        'user_name': request.user.get_full_name(),
                        'csrf_token': get_token(request),
                    })

                except razorpay.errors.BadRequestError as e:
                    logger.error(f"Failed to create Razorpay order: {str(e)}")
                    messages.error(request, "Failed to create Razorpay order. Please try again.")
                    return redirect('cart_detail')
                except Exception as e:
                    logger.error(f"An unexpected error occurred: {str(e)}")
                    messages.error(request, "An unexpected error occurred. Please try again.")
                    return redirect('cart_detail')

            elif payment_method.lower() == 'cod':
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
    def post(self, request):
        # Decode and parse the request body
        decoded_body = request.body.decode('utf-8')
        data = parse_qs(decoded_body)
        data = {k: v[0] for k, v in data.items()}

        payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        signature = data.get('razorpay_signature')
        
        # Retrieve PaymentDetails
        payment_details = get_object_or_404(PaymentDetails, razorpay_order_id=razorpay_order_id)

        # Log the received data for debugging
        logger.info(f"Received data: {data}")
        logger.info(f"razorpay_order_id: {razorpay_order_id}, payment_id: {payment_id}")

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
            order = get_object_or_404(Order, payment_details=payment_details)

            # Retrieve statuses safely, add fallback if not found
            try:
                confirmed_status = OrderStatus.objects.get(status='Confirmed')
            except OrderStatus.DoesNotExist:
                logger.error("OrderStatus with 'Confirmed' status not found.")
                return JsonResponse({'error': 'Confirmed status not found'}, status=500)

            # Check if the 'Completed' status exists, and create it if it doesn't
            try:
                completed_payment_status, created = PaymentStatus.objects.get_or_create(
                    status='Completed', 
                )
                if created:
                    logger.info(f"Created new PaymentStatus: {completed_payment_status}")
            except Exception as e:
                logger.error(f"Error ensuring 'Completed' status exists: {str(e)}")
                return JsonResponse({'error': 'Error checking or creating PaymentStatus'}, status=500)

            # Update order and payment details
            order.status = confirmed_status
            order.payment_details.payment_status = completed_payment_status
            order.payment_details.razorpay_payment_id = payment_id
            order.payment_details.save()
            order.save()

            # Clear user's cart items if necessary
            CartItem.objects.filter(cart__user=order.user).delete()

            return redirect('razorpay_order_success', razorpay_order_id=razorpay_order_id)

        except razorpay.errors.SignatureVerificationError:
            # Handle signature verification error and update payment status to 'Failed'
            payment_details = get_object_or_404(PaymentDetails, razorpay_order_id=razorpay_order_id)
            order = get_object_or_404(Order, payment_details=payment_details)
            try:
                failed_payment_status = PaymentStatus.objects.get(status='Failed')
            except PaymentStatus.DoesNotExist:
                logger.error("PaymentStatus with 'Failed' status not found.")
                return JsonResponse({'error': 'Failed payment status not found'}, status=500)

            order.payment_details.payment_status = failed_payment_status
            order.payment_details.save()
            order.save()
            logger.error("Payment verification failed due to signature mismatch.")
            return redirect('checkout:complete_payment', order_id=order.id)

        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            return JsonResponse({'error': 'An error occurred while processing payment'}, status=500)

@login_required(login_url='accounts:user_login_view')
def razorpay_order_success(request, razorpay_order_id):
    logger.info(f"User logged in: {request.user.is_authenticated}")
    logger.info(f"User ID: {request.user.id}")
    # Find the order related to this Razorpay order ID
    order = get_object_or_404(Order, razorpay_order_id=razorpay_order_id, user=request.user)
    print(order)
    print(razorpay_order_id)

    # Payment verification logic if needed (you might have this handled elsewhere already)
    # Assuming the order is verified, mark it as confirmed
    order.status = 'Confirmed'
    order.payment_date = timezone.now()
    order.save()

    # Clear user's cart items
    CartItem.objects.filter(cart__user=request.user).delete()
    request.session.pop('total_price', None)

    # Show success message and render the Razorpay-specific success page
    return render(request, 'checkout/razorpay_order_success.html', {
        'order': order,
        'total_price': order.total_price,  # Assuming total_price is a field on Order
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
        order = Order.objects.get(id=order_id, user=request.user)

        # Check if the order is eligible for online payment
        if order.payment_details and order.payment_details.payment_method != 'COD':
            try:
                # Initialize Razorpay client
                razorpay_client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))
                total_price = request.session.get('total_price', 0)

                # Create Razorpay order
                razorpay_order = razorpay_client.order.create(data={
                    'amount': total_price,
                    'currency': 'INR',
                    'payment_capture': '1',  # Automatic capture after payment
                })

                # Retrieve Razorpay order ID
                razorpay_order_id = razorpay_order['id']
                order.razorpay_order_id = razorpay_order_id
                order.save()

                # Set the default payment status (ensure it exists in the DB)
                payment_status = PaymentStatus.objects.get(id=PaymentStatus.get_default_payment_status())

                # Create PaymentDetails entry
                payment_details, created = PaymentDetails.objects.get_or_create(
                    payment_method='razorpay',
                    payment_status=payment_status,
                    razorpay_order_id=razorpay_order_id,
                )

                # Link payment details to the order
                order.payment_details = payment_details
                order.save()

                # Store Razorpay order ID in session for verification later
                request.session['razorpay_order_id'] = razorpay_order_id

                # Render the payment page with Razorpay details
                return render(request, 'checkout/complete_payment.html', {
                    'order': order,
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_key': settings.RAZOR_PAY_KEY_ID,  
                    'total_price': total_price *100, 
                    'user_email': request.user.email,
                    'user_name': request.user.get_full_name(),
                    'csrf_token': get_token(request),
                })

            except razorpay.errors.RazorpayError as e:
                # Handle Razorpay API errors gracefully
                logger.error(f"Razorpay API error: {e}")
                return render(request, 'checkout/cod_order_success.html', {
                    'error_message': "There was an issue with the payment gateway. Please try again later."
                })

        else:
            # Handle case where payment method is COD or payment details are missing
            return render(request, 'checkout/cod_order_success.html', {
                'error_message': "This order has already been paid for or is not eligible for online payment."
            })

    except Order.DoesNotExist:
        # Handle case where the order is not found
        return render(request, 'checkout/cod_order_success.html', {
            'error_message': "Order not found."
        })

    except Exception as e:
        # Handle any unexpected errors
        logger.error(f"Unexpected error during payment processing: {str(e)}")
        return render(request, 'checkout/cod_order_success.html', {
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

    if order.status == 'Cancelled by User':
        messages.error(request, 'This order cannot be updated as it has been cancelled by the user.')
        return redirect('list_orders')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status:
            order.status = new_status
            if new_status == 'Delivered':
                order.payment_status = 'Completed'  
            order.save()
            messages.success(request, 'Order status updated successfully.')

    return redirect('list_orders')


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.user.is_superuser:
        order.status = 'Cancelled'
        order.cancellation_reason = 'Cancelled by the team due to technical reasons.'
        order.cancelled_at = timezone.now()
        order.canceled_by = request.user
    else:
        if order.status not in ['Cancelled', 'Delivered']:
            order.status = 'Cancelled'
            order.cancellation_reason = 'Cancelled by User'
            order.cancelled_at = timezone.now()
            order.canceled_by = request.user

    order.save()
    return redirect('my_orders')


@login_required(login_url='accounts:user_login_view')
def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'Delivered':
        order.return_order()
        messages.success(request, "Return request has been submitted.")
    return redirect('order_details', order_id=order_id)
