from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from .forms import *
from .models import * 
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash


User = get_user_model()



@login_required(login_url='accounts:user_login_view')
@never_cache
def upload_profile_picture(request):
    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('user_profile')  # Redirect to profile page after saving
    else:
        form = ProfilePictureForm(instance=request.user)
    return render(request, 'user_profile/upload_profile_picture.html', {'form': form})


@login_required(login_url='accounts:user_login_view')
@never_cache
def user_profile(request):
    user = request.user
    orders = user.orders.all()
    addresses = user.addresses.all()
    
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, instance=user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('user_profile')
    else:
        profile_form = UserProfileForm(instance=user)

    context = {
        'profile_form': profile_form,
        'orders': orders,
        'addresses': addresses,
    }
    return render(request, 'user_profile/user_profile_page.html', context)


@login_required(login_url='accounts:user_login_view')
@never_cache
def edit_profile(request):
    user = request.user  # Get the currently logged-in user

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile was successfully updated!')
            return redirect('user_profile')  # Redirect to the profile page
    else:
        form = UserProfileForm(instance=user)

    return render(request, 'user_profile/edit_profile_page.html', {
        'form': form,
        'profile': user,  # Pass the user instance directly to the template
    })


@login_required(login_url='accounts:user_login_view')
@never_cache
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect('user_profile')
        # Render the template with the form containing errors
        return render(request, 'user_profile/change_password.html', {'form': form})
    else:
        # Render the template with an empty form
        form = CustomPasswordChangeForm(user=request.user)
        return render(request, 'user_profile/change_password.html', {'form': form})

@login_required(login_url='accounts:user_login_view')
@never_cache
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect('user_profile') 
    else:
        form = AddressForm()
    return render(request, 'user_profile/add_address.html', {'form': form})

@login_required(login_url='accounts:user_login_view')
@never_cache
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            return redirect('user_profile')  # or wherever you want to redirect after editing the address
    else:
        form = AddressForm(instance=address)
    return render(request, 'user_profile/edit_address.html', {'form': form})

@login_required(login_url='accounts:user_login_view')
@never_cache
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id)
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted successfully.')
        return redirect('user_profile')  # or wherever you want to redirect after deletion
    return redirect('user_profile')


@login_required(login_url='accounts:user_login_view')
@never_cache
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'Pending':
        order.status = 'Canceled'
        order.save()
        messages.success(request, 'Order has been canceled.')
    else:
        messages.error(request, 'Order cannot be canceled.')

    return redirect('user_profile')
