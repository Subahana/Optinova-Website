from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from .forms import UserProfileForm,ProfilePictureForm,AddressForm,CustomPasswordChangeForm,CancellationForm
from django.http import JsonResponse
from .models import Address
from products.models import ProductVariant
from order_management.models import Order,OrderItem
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from django.middleware.csrf import get_token
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.urls import reverse
from django.utils import timezone 

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
def my_orders(request):
    available_variants = ProductVariant.objects.filter(is_active=True)
    query = request.GET.get('query', '')
    orders = Order.objects.filter(user=request.user)  

    # Filter orders that contain available product variants
    orders = Order.objects.filter(
        user=request.user,  
        items__variant__is_active=True
    ).distinct()

    # Calculate total price and total quantity for each order
    for order in orders:
        order.total_price = order.items.aggregate(
            total=Sum(F('price') * F('quantity'))  # Use 'price' stored in OrderItem
        )['total'] or 0
        
        # Calculate total items in the order
        order.total_items = order.items.aggregate(
            total=Sum('quantity')  # Total quantity of items in this order
        )['total'] or 0

    # Pagination (5 orders per page)
    paginator = Paginator(orders, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'user_profile/my_orders.html', {'page_obj': page_obj, 'query': query})

    
@login_required(login_url='accounts:user_login_view')
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Calculate total price for the order (all items)
    total_price = sum(item.total_price() for item in order.items.all())
    total_price_order = order.total_amount()  # Use the total_amount method

    # Get the cancellation URL
    cancel_order_url = reverse('cancel_order_request', args=[order.id])

    if request.method == 'POST':
        if 'cancel_order' in request.POST and order.status in ['Pending', 'Processing']:
            reason = request.POST.get('cancellation_reason', 'Cancelled by User')
            order.cancel_order(reason=reason)
            messages.success(request, "Order has been cancelled.")
            return redirect('my_orders')

        if 'return_order' in request.POST and order.status == 'Delivered':
            order.return_order()
            messages.success(request, "Return request has been submitted.")
            return redirect('my_orders')

    return render(request, 'checkout/order_details.html', {
        'order': order,
        'total_price_order': total_price_order,
        'total_price': total_price,
        'cancel_order_url': cancel_order_url,  
    })


@login_required(login_url='accounts:user_login_view')
def cancel_order_request(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        form = CancellationForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['cancellation_reason']
            order.status = 'Cancelled'
            order.cancellation_reason = reason  # Save the reason provided by the user
            order.cancelled_at = timezone.now()
            order.canceled_by = request.user  # Log user as the canceller
            order.save()
            messages.success(request, "Your order has been cancelled successfully.")
            return redirect('my_orders')  # Redirect to my orders page
    else:
        form = CancellationForm()

    return render(request, 'user_profile/cancel_order.html', {
        'order': order,
        'form': form,
    })
