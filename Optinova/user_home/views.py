from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from products.models import Product, Category,ProductVariant
from offer_management.models import CategoryOffer
from cart_management.models import Wishlist
from brand_management.models import Brand
from products.forms import ProductVariantForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth import logout
from django.middleware.csrf import get_token
from django.db.models import Prefetch,Exists, OuterRef,Subquery,F
from django.http import JsonResponse
from django.db.models import Prefetch
from django.utils import timezone
from user_wallet.models import Wallet
from itertools import chain



@login_required(login_url='accounts:user_login_view')
def user_product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if not product.is_active:
        messages.warning(request, 'This product is inactive. Redirecting to the shop.')
        return redirect('shop')

    if not product.category.is_active:
        messages.warning(request, 'The category of this product is not active. Redirecting to the shop.')
        return redirect('shop')

    main_variant = product.variants.first()  # Fetch the main variant

    # Get active offers for the product's category
    active_offers = CategoryOffer.objects.filter(
        category=product.category,
        is_active=True
    )

    # Fetch related products
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).prefetch_related(
        Prefetch('variants', queryset=ProductVariant.objects.filter(is_active=True))
    ).order_by('?')[:4]

    categories = Category.objects.filter(is_active=True)

    # Prepare variant data with original and discounted prices
    variant_prices = []
    for variant in product.variants.filter(is_active=True):
        original_price = variant.price
        discounted_price = variant.get_discounted_price()  # Get the discounted price
        variant_prices.append({
            'variant': variant,
            'original_price': original_price,
            'discounted_price': discounted_price,
        })
        
    context = {
        'product': product,
        'main_variant': main_variant,
        'variant_prices': variant_prices,  # Pass variant prices to the template
        'related_products': related_products,
        'active_offers': active_offers,
        'categories': categories,
    }

    return render(request, 'user_home/shop_details.html', context)


def shop(request):
    # Fetch categories, products, brands, and active offers
    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    active_offers = CategoryOffer.objects.filter(is_active=True)
    user_wishlist = Wishlist.objects.filter(user=request.user).values_list('variants__id', flat=True)
    categories_with_offers = categories.prefetch_related(Prefetch('offers', queryset=active_offers))
    products_with_offers = products.prefetch_related('category', 'variants')

    # Apply discount to each product
    for product in products_with_offers:
        main_variant = product.main_variant  # Assuming main_variant returns the main variant object
        product.discounted_price = main_variant.get_discounted_price()

    # Search functionality
    query = request.GET.get('q')
    if query:
        products_with_offers = products_with_offers.filter(name__icontains=query)

    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        products_with_offers = products_with_offers.filter(category_id=category_id)

    # Filter by brand
    brand_id = request.GET.get('brand')
    if brand_id:
        products_with_offers = products_with_offers.filter(brand_id=brand_id)

    # Sorting functionality
    sort_option = request.GET.get('sort')
    if sort_option == 'price_low':
        products_with_offers = products_with_offers.order_by('main_variant__discounted_price')
    elif sort_option == 'price_high':
        products_with_offers = products_with_offers.order_by('-main_variant__discounted_price')
    elif sort_option == 'a_to_z':
        products_with_offers = products_with_offers.order_by('name')
    elif sort_option == 'z_to_a':
        products_with_offers = products_with_offers.order_by('-name')

    # Total number of products per page
    per_page = 6

    # Initialize Paginator with the filtered products and per_page value
    paginator = Paginator(products_with_offers, per_page)

    # Get the current page number from the request (defaults to 1 if not specified)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # If the filtered category has fewer than 5 products, adjust pages accordingly
    if len(page_obj.object_list) < per_page and page_obj.has_next():
        next_page_obj = paginator.get_page(page_obj.next_page_number())
        remaining_items_needed = per_page - len(page_obj.object_list)
        
        # Add the remaining items from the next page to the first page
        page_obj.object_list += next_page_obj.object_list[:remaining_items_needed]

        # If you added items to the first page, reduce the remaining items from the next page
        next_page_obj.object_list = next_page_obj.object_list[remaining_items_needed:]

    # Ensure only products from the filtered category are displayed, no other products
    # If the category is applied, all products on the second page should also belong to the filtered category
    if category_id:
        page_obj.object_list = page_obj.object_list.filter(category_id=category_id)

    # Prepare context for rendering
    context = {
        'products': page_obj,
        'categories': categories_with_offers,
        'brands': brands,
        'user_wishlist': user_wishlist,
        'page_obj': page_obj,
        'csrf_token': get_token(request),
    }

    return render(request, 'user_home/shop.html', context)


@login_required(login_url='accounts:user_login_view')
def user_home(request):

    if request.user.is_superuser:
        messages.error(request, 'Admin users are not allowed to access the user home page.')
        return redirect('admin_page')  

    products = Product.objects.filter(
        is_active=True,
        category__is_active=True
    ).prefetch_related('variants') 
    # Fetch active offers for the categories of the products
    active_offers = CategoryOffer.objects.filter(
        category__in=products.values_list('category', flat=True),
        is_active=True
    )
    context = {
        'products': products,
        'active_offers': active_offers,
    }
    return render(request, 'user_home/index.html', context)


# View to handle user logout
@login_required(login_url='accounts:user_login_view')
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    # Redirect to a specific page after logout or default to home
    return redirect(request.GET.get('next', 'accounts:first_page'))
