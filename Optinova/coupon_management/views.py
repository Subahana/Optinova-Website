from django.shortcuts import render, redirect, get_object_or_404
from .models import Coupon
from .forms import CouponForm
from django.contrib import messages

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
