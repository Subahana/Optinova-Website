from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from products.models import Product,Category
from django.contrib import messages
from django.contrib.auth import logout

# Create your views here.


@login_required(login_url='accounts:user_login_view')  
@never_cache
def user_product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]  # Adjust the number as needed
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'user_home/shop_details.html', context)


@login_required(login_url='accounts:user_login_view')  
@never_cache
def shop(request):
    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    
    context = {
        'categories': categories,
        'products': products,
    }
    return render(request, 'user_home/shop.html', context)

@login_required(login_url='accounts:user_login_view')  
@never_cache
def user_home(request):
    # Check if the user is a superuser
    if request.user.is_superuser:
        messages.error(request, 'Admin users are not allowed to access the user home page.')
        return redirect('admin_page')  # Redirect to admin page or another appropriate page
    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    
    context = {
        'categories': categories,
        'products': products,
    }
    return render(request, 'user_home/index.html',context)

@login_required(login_url='accounts:user_login_view')  
@never_cache
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('accounts:first_page')

