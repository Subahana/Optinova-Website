from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Order, OrderItem
from user_profile.models import Address
from cart_management.models import Cart, CartItem
from .forms import OrderForm
from django.contrib import messages
from django.db import transaction
from django.db.models import Q

@login_required
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    
    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
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
                    address = Address.objects.get(id=address_id)
                
                payment_method = form.cleaned_data['payment_method']
                
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    payment_method=payment_method
                )
                
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
                
                cart_items.delete()
                
                return redirect('order_success', order_id=order.id)
        else:
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
    return render(request, 'checkout/order_success.html', {'order': order, 'total_price': total_price})



def list_orders(request):
    orders = Order.objects.all()  # Start with all orders

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
            order.save()
            messages.success(request, 'Order status updated successfully.')

    return redirect('list_orders')


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status != 'Cancelled by User':
        order.status = 'Cancelled by User'
        order.canceled_by = request.user  # Set the user who canceled the order
        order.save()
    return render(request,"user_profile/order_details.html")  # Redirect to the order list or appropriate page
