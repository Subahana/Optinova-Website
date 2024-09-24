from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from user_profile.models import Address

# Create your views here.

User = get_user_model()

@login_required(login_url='accounts:admin_login')  
@never_cache
def user_management_page(request):
    status = request.GET.get('status')
    search_query = request.GET.get('search', '')
    
    # Start with filtering by status and exclude superusers
    if status == 'active':
        users = User.objects.filter(is_active=True, is_superuser=False)
    elif status == 'inactive':
        users = User.objects.filter(is_active=False, is_superuser=False)
    else:
        users = User.objects.filter(is_superuser=False)
    
    # Apply search filter
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query) | 
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query)
        )
    
    context = {
        'users': users,
        'search_query': search_query,
        'status': status,
    }
    return render(request, 'admin_page/user_management_page.html', context)

@login_required(login_url='accounts:admin_login')  
@never_cache
def permanent_delete_user(request, id):
    user = get_object_or_404(User, id=id)
    if request.method == "POST":
        # Ensure user is not a superuser before deleting
        if not user.is_superuser:
            user.delete()
            messages.success(request, 'User has been deleted permanently.')
        else:
            messages.error(request, 'Superuser cannot be deleted.')
    return redirect('user_management_page')

@login_required(login_url='accounts:admin_login')  
@never_cache
def block_user(request, id):
    user = get_object_or_404(User, id=id)
    if request.method == "POST":
        if not user.is_superuser:
            user.is_active = False
            user.save()
            messages.success(request, f"User {user.username} has been blocked.")
        else:
            messages.error(request, 'Superuser cannot be blocked.')
    return redirect('user_details_page', id=id)  # Redirect back to the user's detail page

@login_required(login_url='accounts:admin_login')  
def unblock_user(request, id):
    user = get_object_or_404(User, id=id)
    if request.method == "POST":
        if not user.is_superuser:
            user.is_active = True
            user.save()
            messages.success(request, f"User {user.username} has been unblocked.")
        else:
            messages.error(request, 'Superuser cannot be unblocked.')
    return redirect('user_details_page', id=id)  # Redirect back to the user's detail page

@login_required(login_url='accounts:admin_login')  
def user_details_page(request, id):
    user = get_object_or_404(User, id=id)  # Adjust User to your actual model
    addresses = Address.objects.filter(user=user)  # Fetch all addresses related to the user
    context = {
        'user': user,
        'addresses' : addresses,
    }
    return render(request, 'admin_page/user_details_page.html', context)

@login_required(login_url='accounts:admin_login')  
def admin_page(request):
    return render(request,'admin_page/index.html')

@login_required(login_url='accounts:admin_login')  
def admin_logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('accounts:admin_login')
