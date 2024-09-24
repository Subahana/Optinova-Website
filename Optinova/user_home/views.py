from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from products.models import Product, Category,ProductVariant
from django.contrib import messages
from django.contrib.auth import logout
from django.middleware.csrf import get_token
from django.db.models import Prefetch


@login_required(login_url='accounts:user_login_view')
@never_cache
def user_product_detail(request, product_id):
    # Get the current product
    product = get_object_or_404(Product, id=product_id)

    # Check if the product is inactive
    if not product.is_active:
        messages.warning(request, 'This product is inactive. Redirecting to the shop.')
        return redirect('shop')

    # Check if the product's category is inactive
    if not product.category.is_active:
        messages.warning(request, 'The category of this product is not active. Redirecting to the shop.')
        return redirect('shop')

    # Fetch the main variant for the product
    main_variant = product.variants.first()  # Assuming 'variants' related name

    # Get related products from the same category
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).prefetch_related(
        Prefetch('variants', queryset=ProductVariant.objects.filter(is_active=True))
    ).order_by('?')[:4]  # Fetch related products and their active variants

    # Pass related products and variants to the template
    categories = Category.objects.filter(is_active=True)

    context = {
        'product': product,
        'main_variant': main_variant,  # Main variant of the current product
        'related_products': related_products,  # Related products with their variants
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
        return redirect('admin_page')  

    products = Product.objects.filter(
        is_active=True,
        category__is_active=True
    )


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
