from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import  Order, OrderItem
from user_profile.models import Address
from cart_management.models import  Cart, CartItem
from .forms import OrderForm

@login_required
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            address = form.cleaned_data['address_id']
            payment_method = form.cleaned_data['payment_method']
            
            order = Order.objects.create(
                user=request.user,
                address=address,
                payment_method=payment_method
            )
            
            cart_items = CartItem.objects.filter(cart=cart)
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    quantity=item.quantity,
                    price=item.variant.price
                )
                # Optionally, update stock here
                item.variant.stock -= item.quantity
                item.variant.save()
            
            # Clear the cart
            cart_items.delete()
            
            return redirect('order_success')
    else:
        form = OrderForm(user=request.user)
    
    return render(request, 'checkout/checkout.html', {'form': form})

def order_success(request):
    return render(request, 'checkout/order_success.html')
