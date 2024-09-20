from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from .forms import UserProfileForm,ProfilePictureForm,AddressForm
from django.http import JsonResponse
from django.contrib.auth.forms import PasswordChangeForm
from .models import Address
from order_management.models import Order,OrderItem
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from django.middleware.csrf import get_token

User = get_user_model()

@login_required(login_url='accounts:user_login_view')
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
def user_profile(request):
    user = request.user
    addresses = user.addresses.all()
    orders = Order.objects.filter(user=user)

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
        'addresses': addresses,
        'orders': orders,

    }
    return render(request, 'user_profile/user_profile_page.html', context)


@login_required(login_url='accounts:user_login_view')
def edit_profile(request):
    user = request.user  # Get the currently logged-in user

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile was successfully updated!')
            return redirect('user_profile')  # Redirect to the profile page
        else:
            print(form.errors)
    else:
        form = UserProfileForm(instance=user)

    return render(request, 'user_profile/edit_profile_page.html', {
        'form': form,
        'profile': user,  # Pass the user instance directly to the template
    })

@login_required(login_url='accounts:user_login_view')
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'message': 'Password changed successfully!'}, status=200)
            return redirect('user_profile')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {field: form.errors[field][0] for field in form.errors}
                return JsonResponse({'errors': errors}, status=400)
    else:
        # Initialize the form for GET requests
        form = PasswordChangeForm(request.user)

    return render(request, 'user_profile/change_password.html', {'form': form})


@login_required(login_url='accounts:user_login_view')
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
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id)
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted successfully.')
        return redirect('user_profile')  # or wherever you want to redirect after deletion
    return redirect('user_profile')

@login_required(login_url='accounts:user_login_view')
def order_details(request):
    # Fetch the user's orders
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    # Fetch all the order items for each order and group them by order
    order_details = []
    for order in orders:
        items = OrderItem.objects.filter(order=order)
        order_details.append({
            'order': order,
            'items': items
        })
    
    context = {
        'order_details': order_details,
    }

    return render(request, 'user_profile/order_details.html', context)
