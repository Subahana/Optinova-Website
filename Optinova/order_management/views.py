from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Order, OrderItem
from user_profile.models import Address
from cart_management.models import Cart, CartItem
from .forms import OrderForm
from django.contrib import messages
from django.db import transaction

@login_required
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    
    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            print("Form is valid")
            with transaction.atomic():
                address_id = form.cleaned_data.get('address')
                
                # Handle the case where a new address is being added
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
                    # Use existing address
                    address = Address.objects.get(id=address_id)
                    print(f"Selected address: {address}")
                
                payment_method = form.cleaned_data['payment_method']
                
                # Create the order
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    payment_method=payment_method
                )
                print(f"Order created: {order}")
                
                # Process each item in the cart
                cart_items = CartItem.objects.filter(cart=cart)
                if not cart_items.exists():
                    messages.error(request, "Your cart is empty.")
                    return redirect('cart_view')
                
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        variant=item.variant,
                        quantity=item.quantity,
                        price=item.variant.price
                    )
                    print(f"OrderItem created for product {item.variant.product.name}")
                
                # Clear the cart after the order is placed
                cart_items.delete()
                print("Cart cleared.")
                
                return redirect('order_success', order_id=order.id)
        else:
            print("Form is not valid")
            print(form.errors)  # Print form errors
    else:
        form = OrderForm(user=request.user)
    
    return render(request, 'checkout/checkout.html', {
        'form': form,
        'addresses': addresses,
        'cart_items': CartItem.objects.filter(cart=cart),
        'total_price': cart.get_total_price(),
    })



def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    total_price = sum(item.quantity * item.variant.price for item in order.items.all())

    return render(request, 'checkout/order_success.html', {'order': order,'total_price':total_price})

# Admin-side Order Management

def list_orders(request):
    orders = Order.objects.all()
    return render(request, 'checkout/list_orders.html', {'orders': orders})


def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status:
            order.status = new_status
            order.save()
    
    return redirect('list_orders')  # Redirect to the order management page



@login_required
def cancel_order(request, order_id):
    # Fetch the order object
    order = get_object_or_404(Order, id=order_id)

    # Check if the logged-in user is authorized to cancel this order
    if request.user != order.user and not request.user.is_superuser:
        messages.error(request, 'You are not authorized to cancel this order.')
        return redirect('order_details')  # Redirect to user-side orders page or an appropriate page

    # Check if the order can be cancelled
    if not order.is_cancelled:
        order.cancel_order()  # Uses the cancel_order method defined in the model
        messages.success(request, f'Order {order_id} has been cancelled.')
    else:
        messages.error(request, f'Order {order_id} is already cancelled.')

    # Redirect based on user role
    if request.user.is_superuser:
        return redirect('list_orders')  # Replace with the actual URL name for admin orders list
    else:
        return redirect('order_details')  # Replace with the actual URL name for user orders list
