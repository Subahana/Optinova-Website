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
from django.middleware.csrf import get_token


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

            # Create an order
            order = Order.objects.create(
                user=request.user,
                address=address,
                payment_method=payment_method,
            )

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

            if total_price <= 0:
                messages.error(request, "Total price is invalid.")
                return redirect('cart_detail')

            if payment_method.lower() == 'razorpay':
                try:
                    razorpay_client = razorpay.Client(auth=(settings.RAZOR_PAY_KEY_ID, settings.RAZOR_PAY_KEY_SECRET))

                    razorpay_order = razorpay_client.order.create({
                        "amount": total_price,
                        "currency": "INR",
                        "payment_capture": 1
                    })
                    
                    logger.info(f"Razorpay order created with ID: {razorpay_order['id']}")

                    order.razorpay_order_id = razorpay_order['id']
                    
                    order.save()
                    request.session['razorpay_order_id'] = order.razorpay_order_id
                    request.session.modified = True  # Explicitly mark the session as modified
                    print('before razor', order.razorpay_order_id)


                    return render(request, 'checkout/razorpay_payment.html', {
                        'order': order,
                        'razorpay_order_id': order.razorpay_order_id,
                        'razorpay_key': settings.RAZOR_PAY_KEY_ID,
                        'total_price': total_price, 
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
                return redirect('order_success', order_id=order.id)

    else:
        form = OrderForm(user=request.user)

    return render(request, 'checkout/checkout.html', {
        'form': form,
        'addresses': addresses,
        'cart_items': CartItem.objects.filter(cart=cart),
        'total_price': total_price,
        'csrf_token': get_token(request),

    })


@csrf_exempt
@login_required(login_url='accounts:user_login_view')
def verify_razorpay_payment(request):
    if request.method == "POST":
        print('verify_start')
        payment_id = request.POST.get("razorpay_payment_id")
        signature = request.POST.get("razorpay_signature")
        order_id = request.POST.get("razorpay_order_id")

        # Ensure all necessary fields are present
        if not payment_id or not signature or not order_id:
            messages.error(request, "Missing payment information.")
            return redirect('cart')

        # Set up Razorpay client
        client = razorpay.Client(auth=("YOUR_RAZORPAY_KEY", "YOUR_RAZORPAY_SECRET"))

        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }

        try:
            print('hi')
            # Verify payment signature
            client.utility.verify_payment_signature(params_dict)

            # Clear the cart items for the user
            cart = Cart.objects.get(user=request.user)
            CartItem.objects.filter(cart=cart).delete()

            # Update the order status to 'paid'
            order = get_object_or_404(Order, razorpay_order_id=order_id, razorpay_payment_id=payment_id)
            order.status = 'paid'
            order.save()
            messages.success(request, "Payment successful! Your order has been placed.")
            print('Payment successful - redirecting to success page.')
            
            # Redirect to the order success page
            return redirect('order_success', order_id=order_id)

        except razorpay.errors.SignatureVerificationError:
            messages.error(request, "Payment verification failed. Please try again.")

            # Attempt to parse error metadata if present
            metadata_json = request.POST.get('error[metadata]')
            order_id = None  # Default if parsing fails

            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                    order_id = metadata.get('order_id')
                except json.JSONDecodeError:
                    pass

            # Redirect to the order failure page
            return redirect('order_failure', order_id=order_id if order_id else '')

    # Fallback for non-POST requests
    return redirect('cart')

def order_success(request, order_id):
    order = get_object_or_404(Order, razorpay_order_id=order_id)
    total_price = sum(item.quantity * item.variant.price for item in order.items.all())
    payment_status = "Paid" if order.payment_method.lower() == "razorpay" else "Cash on Delivery"

    return render(request, 'checkout/order_success.html', {
        'order': order,
        'total_price': total_price,
        'payment_status': payment_status,
    })

@login_required(login_url='accounts:user_login_view')
def order_failure(request, order_id):
    order = get_object_or_404(Order, razorpay_order_id=order_id)
    total_price = sum(item.quantity * item.variant.price for item in order.items.all())
    payment_status = "Failed"

    return render(request, 'checkout/order_failure.html', {
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


@login_required(login_url='accounts:user_login_view')
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