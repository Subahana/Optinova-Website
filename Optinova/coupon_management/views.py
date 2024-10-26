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
            coupon_code = data.get('coupon_code', '').strip()
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid data format.'}, status=400)

        try:
            # Fetch the user's cart
            user_cart = get_object_or_404(Cart, user=request.user)
            cart_items = CartItem.objects.filter(cart=user_cart)
            total_items = sum(item.quantity for item in cart_items)

            # Check if the cart is empty
            if not cart_items.exists():
                return JsonResponse({'success': False, 'error': 'Your cart is empty.'}, status=400)

            # Calculate the original total price of all items in the cart
            original_total = user_cart.get_original_total()  # You likely have a method to calculate this

            # Fetch the coupon (case-insensitive search)
            coupon = Coupon.objects.filter(code__iexact=coupon_code, active=True).first()
            if coupon is None:
                return JsonResponse({'success': False, 'error': 'Invalid coupon code'}, status=400)

            # Check if the coupon is valid (active, within date range)
            current_time = timezone.now()
            if coupon.valid_from <= current_time <= coupon.valid_to:
                # Ensure the user hasn't already used the coupon in a completed order
                used_coupon = Order.objects.filter(user=request.user, coupon=coupon, status='completed').exists()
                
                if used_coupon:
                    return JsonResponse({'success': False, 'error': 'You have already used this coupon for a completed order.'}, status=400)

                # Calculate the discount based on the entire cart total
                discount_amount = coupon.get_discount_amount(original_total)
                discount_amount = min(discount_amount, original_total)  # Ensure discount doesn't exceed total

                # Calculate the new total after applying the discount
                new_total = original_total - discount_amount

                # Save the coupon to the cart
                user_cart.coupon = coupon
                user_cart.save()

                return JsonResponse({
                    'success': True,
                    'original_total': original_total,
                    'new_total': float(new_total),
                    'discount_amount': float(discount_amount),
                    'total_items': total_items
                })

            else:
                return JsonResponse({'success': False, 'error': 'Coupon is not valid or expired'}, status=400)
        
        except Exception as e:
            # Log unexpected errors
            print(f"Error applying coupon: {e}")
            return JsonResponse({'success': False, 'error': 'Something went wrong on the server.'}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


def remove_coupon(request):
    if request.method == 'POST':
        try:
            # Fetch the user's cart
            user_cart = get_object_or_404(Cart, user=request.user)

            # Check if a coupon is applied
            if user_cart.coupon:
                # Remove the coupon
                user_cart.coupon = None
                user_cart.save()

                # Recalculate totals without the discount
                original_total = user_cart.get_original_total()
                new_total = original_total  # Since there is no discount now
                total_items = sum(item.quantity for item in user_cart.cartitem_set.all())

                # Return updated cart data
                return JsonResponse({
                    'success': True,
                    'original_total': original_total,
                    'new_total': new_total,
                    'discount_amount': 0,  # No discount after removal
                    'total_items': total_items
                })

            return JsonResponse({'success': False, 'error': 'No coupon applied.'}, status=400)
        
        except Exception as e:
            print(f"Error removing coupon: {e}")
            return JsonResponse({'success': False, 'error': 'Failed to remove the coupon.'}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
