from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Order, OrderItem
from user_profile.models import Address
from cart_management.models import Cart, CartItem
from .forms import OrderForm
from django.contrib import messages
import razorpay
from django.conf import settings
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import logging 

logger = logging.getLogger(__name__)

@login_required(login_url='accounts:user_login_view')
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    addresses = Address.objects.filter(user=request.user)

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

            # Create the order
            order = Order.objects.create(
                user=request.user,
                address=address,
                payment_method=payment_method,
            )

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

            # Calculate total price for the payment
            total_price = int(cart.get_total_price() * 100)  # Convert to paisa
            logger.debug(f"Total price calculated in paisa: {total_price}")

            # Handle payment method: Razorpay, COD, etc.
            if payment_method.lower() == 'razorpay':
                try:
                    razorpay_client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))

                    # Create Razorpay order
                    razorpay_order = razorpay_client.order.create({
                        "amount": total_price,
                        "currency": "INR",
                        "payment_capture": 1
                    })
                    
                    logger.info(f"Razorpay order created with ID: {razorpay_order['id']}")

                    order.razorpay_order_id = razorpay_order['id']
                    order.save()
                    
                    # Pass Razorpay data to the frontend for payment
                    return render(request, 'checkout/razorpay_payment.html', {
                        'order': order,
                        'razorpay_order_id': order.razorpay_order_id,
                        'razorpay_key': settings.RAZOR_PAY_KEY_ID,
                        'total_price': total_price,  # Keep amount in paisa
                        'user_email': request.user.email,
                        'user_name': request.user.get_full_name(),
                    })
                except razorpay.errors.BadRequestError as e:
                    logger.error(f"Failed to create Razorpay order: {str(e)}")
                    messages.error(request, "Failed to create Razorpay order. Please try again.")
                    return redirect('cart_detail')
                except Exception as e:
                    logger.error(f"An error occurred: {str(e)}")
                    messages.error(request, "An unexpected error occurred. Please try again.")
                    return redirect('cart_detail')

            elif payment_method.lower() == 'cod':
                cart_items.delete()  # Clear cart after creating order
                messages.success(request, "Order placed successfully with Cash on Delivery.")
                return redirect('order_success', order_id=order.id)

    else:
        form = OrderForm(user=request.user)

    return render(request, 'checkout/checkout.html', {
        'form': form,
        'addresses': addresses,
        'cart_items': CartItem.objects.filter(cart=cart),
        'total_price': cart.get_total_price(),
    })


@csrf_exempt
def verify_razorpay_payment(request):
    if request.method == "POST":
        data = json.loads(request.body)
        order_id = data.get("order_id")
        payment_id = data.get("payment_id")

        logger.debug(f"Verifying Razorpay payment: Order ID - {order_id}, Payment ID - {payment_id}")

        # Skip verification in test mode
        if settings.RAZORPAY_TEST_MODE:  # Ensure this setting exists
            order = get_object_or_404(Order, razorpay_order_id=order_id)
            order.status = 'Paid'
            order.save()
            logger.info(f"Order {order.id} marked as paid in test mode")
            return JsonResponse({'success': True, 'order_id': order.id})

        # Production mode payment verification
        client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))
        try:
            client.utility.verify_payment_signature({
                'order_id': order_id,
                'payment_id': payment_id,
            })

            # Update order status to Paid
            order = get_object_or_404(Order, razorpay_order_id=order_id)
            order.status = 'Paid'
            order.save()
            logger.info(f"Order {order.id} payment verified and marked as paid")

            return JsonResponse({'success': True, 'order_id': order.id})
        except razorpay.errors.SignatureVerificationError as e:
            logger.error(f"Payment verification failed: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            return JsonResponse({'error': 'An unexpected error occurred.'}, status=400)

    return JsonResponse({'error': 'Invalid request.'}, status=400)


@login_required(login_url='accounts:user_login_view')
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    total_price = sum(item.quantity * item.variant.price for item in order.items.all())
    payment_status = "Paid" if order.payment_method.lower() == "razorpay" else "Cash on Delivery"

    return render(request, 'checkout/order_success.html', {
        'order': order,
        'total_price': total_price,
        'payment_status': payment_status,
    })


def list_orders(request):
    orders = Order.objects.filter(items__variant__is_active=True).distinct()

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(user__username__icontains=search_query)

    # Filter by status
    status_filter = request.GET.get('status_filter', '')
    if status_filter:
        orders = orders.filter(status=status_filter)

    # Sorting
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

    # Check if the user is an admin
    if request.user.is_superuser:  # Adjust this to your actual admin check logic
        order.status = 'Cancelled'
        order.cancellation_reason = 'Cancelled by the team due to technical reasons.'  # Custom message
        order.cancelled_at = timezone.now()
        order.canceled_by = request.user  # Log admin as the canceller
    else:
        if order.status not in ['Cancelled', 'Delivered']:
            order.status = 'Cancelled'
            order.cancellation_reason = 'Cancelled by User'  # Log user cancellation reason
            order.cancelled_at = timezone.now()  # Log cancellation time
            order.canceled_by = request.user  # Log user as the canceller

    order.save()
    return redirect('my_orders')  # Redirect back to the orders page


@login_required(login_url='accounts:user_login_view')
def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'Delivered':
        order.return_order()
        messages.success(request, "Return request has been submitted.")
    return redirect('order_details', order_id=order_id)


