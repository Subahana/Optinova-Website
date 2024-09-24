from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from .forms import UserProfileForm,ProfilePictureForm,AddressForm,CustomPasswordChangeForm
from django.http import JsonResponse
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

@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True}, status=200)  # Respond with success

        # If form is invalid, send errors back in JSON format
        errors = {field: error[0] for field, error in form.errors.items()}
        return JsonResponse({'errors': errors}, status=400)
    
    # In case it's not a POST request, render the template
    form = CustomPasswordChangeForm(user=request.user)
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
