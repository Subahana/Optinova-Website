from django.shortcuts import render, redirect, get_object_or_404
from .models import Coupon
from order_management.models import Order
from .forms import CouponForm
from django.contrib import messages
import json
from django.http import JsonResponse
from cart_management.models import Cart ,CartItem
from django.utils import timezone
from django.db.models import Q

def create_coupon(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('coupon_list')
    else:
        form = CouponForm()
    return render(request, 'coupon/create_coupon.html', {'form': form})


def edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)  

    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)  
        if form.is_valid():
            form.save()  
            return redirect('coupon_list')  
    else:
        form = CouponForm(instance=coupon)  

    context = {
        'form': form,
    }
    return render(request, 'coupon/edit_coupon.html', context)


def coupon_list(request):
    coupons = Coupon.objects.all()  # Retrieve all coupons from the database
    context = {
        'coupons': coupons,
    }
    return render(request, 'coupon/coupon_list.html', context)


def coupon_status(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.active = not coupon.active
    coupon.save()

    if coupon.active:
        messages.success(request, f'Coupon "{coupon.code}" has been activated.')
    else:
        messages.warning(request, f'Coupon "{coupon.code}" has been deactivated.')

    return redirect('coupon_list')



def apply_coupon(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body) 
            coupon_code = data.get('coupon_code', '').strip()  # Ensure no leading/trailing spaces
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid data format.'})

        # Get the user's cart
        user_cart = get_object_or_404(Cart, user=request.user)
        cart_items = CartItem.objects.filter(cart=user_cart)
        total_items = sum(item.quantity for item in cart_items)

        # Check if the cart contains any items
        if not user_cart.cartitem_set.exists():
            return JsonResponse({'success': False, 'error': 'Your cart is empty.'})

        original_total = user_cart.get_original_total()  # Calculate original cart total

        # Fetch the coupon (case-insensitive search)
        coupon = Coupon.objects.filter(code__iexact=coupon_code, active=True).first()
        if coupon is None:
            return JsonResponse({'success': False, 'error': 'Invalid coupon code'})

        # Check if the coupon is valid (active, within date range)
        current_time = timezone.now()
        if coupon.valid_from <= current_time <= coupon.valid_to:
            # Coupon is valid, apply the discount
            discount_amount = coupon.get_discount_amount(original_total)
            discount_amount = min(discount_amount, original_total)  # Ensure discount doesn't exceed total

            new_total = original_total - discount_amount

            # Save coupon to cart
            user_cart.coupon = coupon
            user_cart.save()

            return JsonResponse({
                'success': True,
                'new_total': float(new_total),  # Float for proper JSON serialization
                'discount_amount': float(discount_amount),
                'total_items': total_items  

            })
        else:
            return JsonResponse({'success': False, 'error': 'Coupon is not valid or expired'})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

