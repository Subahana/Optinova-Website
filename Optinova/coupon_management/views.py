from django.shortcuts import render, redirect, get_object_or_404
from .models import Coupon
from order_management.models import Order
from .forms import CouponForm
from django.contrib import messages
import json
from django.http import JsonResponse
from cart_management.models import Cart 

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
        coupon_code = request.POST.get('coupon_code')
        cart_total = request.session.get('cart_total', 0)
        print("Received coupon code:", coupon_code)  # Debugging line

        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)
            print("Coupon found: B", coupon)
            if not coupon.active:
                return JsonResponse({'success': False, 'error': 'Coupon is not active'})
            if coupon.is_valid():
                discount_amount = coupon.get_discount_amount(cart_total)
                new_total = cart_total - discount_amount
                request.session['applied_coupon'] = coupon_code
                request.session['discount_amount'] = discount_amount
                request.session['new_total'] = new_total
                print("Coupon found:", coupon)

                return JsonResponse({
                    'success': True,
                    'new_total': new_total,
                    'discount_amount': discount_amount
                })
            else:
                return JsonResponse({'success': False, 'error': 'Coupon is not valid or expired'})
        except Coupon.DoesNotExist:
            print("Coupon not found or not active.")
            return JsonResponse({'success': False, 'error': 'Invalid coupon code'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
