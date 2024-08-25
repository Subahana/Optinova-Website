from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from products.models import Product, Category
from django.contrib import messages
from django.contrib.auth import logout

@login_required(login_url='accounts:user_login_view')
@never_cache
def user_product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Check if the product is inactive
    if not product.is_active:
        messages.warning(request, 'This product is inactive. Redirecting to the shop.')
        return redirect('shop')  # Redirect to the shop page

    # Check if the product's category is inactive
    if not product.category.is_active:
        messages.warning(request, 'The category of this product is not active. Redirecting to the shop.')
        return redirect('shop')  # Redirect to the shop page

    categories = Category.objects.filter(is_active=True)
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).order_by('?')[:4]  
    
    context = {
        'product': product,
        'related_products': related_products,
        'categories': categories,
    }
    return render(request, 'user_home/shop_details.html', context)


# View to show the shop page with product and category lists
@login_required(login_url='accounts:user_login_view')
@never_cache
def shop(request):
    # Filter categories and products based on active status
    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(
        is_active=True,
        category__in=categories
    )
    
    context = {
        'categories': categories,
        'products': products,
    }
    return render(request, 'user_home/shop.html', context)


@login_required(login_url='accounts:user_login_view')
@never_cache
def user_home(request):
    
    if request.user.is_superuser:
        messages.error(request, 'Admin users are not allowed to access the user home page.')
        return redirect('admin_page')  # Redirect to admin page or another appropriate page

    products = Product.objects.filter(
        is_active=True,
        category__is_active=True
    )  # Fetch all products with active categories

    context = {
        'products': products,
    }
    return render(request, 'user_home/index.html', context)


# View to handle user logout
@login_required(login_url='accounts:user_login_view')
@never_cache
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    # Redirect to a specific page after logout or default to home
    return redirect(request.GET.get('next', 'accounts:first_page'))
