from django.shortcuts import get_object_or_404, redirect,render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Cart, CartItem
from products.models import ProductVariant
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token
import logging

logger = logging.getLogger(__name__)

@login_required(login_url='accounts:user_login_view')
def add_to_cart(request, variant_id):
    if request.method == "POST":
        quantity = request.POST.get('quantity', 1)
        try:
            quantity = int(quantity)
        except ValueError:
            return JsonResponse({'message': 'Invalid quantity', 'status': 'error'})
        
        variant = get_object_or_404(ProductVariant, id=variant_id)
        user = request.user
        
        # Retrieve or create the user's cart
        cart, created = Cart.objects.get_or_create(user=user)
        
        # Check if item already exists in the cart
        cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()

        return JsonResponse({'message': 'Item added to cart successfully', 'status': 'success'})
    return JsonResponse({'message': 'Invalid request method', 'status': 'error'})


@login_required(login_url='accounts:user_login_view')
def cart_detail(request):
    try:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        total_price = sum(item.total_price() for item in cart_items)
        total_items = sum(item.quantity for item in cart_items)

        all_variants = ProductVariant.objects.all()
        in_cart_variants = cart_items.values_list('variant_id', flat=True)
        variants_not_in_cart = all_variants.exclude(id__in=in_cart_variants)

        return render(request, 'cart_management/cart_detail.html', {
            'cart_items': cart_items,
            'total_price': total_price,
            'variants_not_in_cart': variants_not_in_cart,
            'total_items' : total_items,
            'csrf_token': get_token(request),
        })
    except Exception as e:
        logger.error(f"Error in cart_detail view: {e}", exc_info=True)
        return JsonResponse({'error': 'An error occurred.'}, status=500)


@login_required(login_url='accounts:user_login_view')
@require_POST
def update_cart_item_quantity(request, cart_item_id):
    try:
        cart_item = CartItem.objects.get(id=cart_item_id)
        new_quantity = int(request.POST.get('quantity', 1))
        
        if new_quantity > 0:
            cart_item.quantity = new_quantity
            cart_item.save()
        else:
            cart_item.delete()

        # If it's an AJAX request, return a JSON response
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'new_quantity': cart_item.quantity if new_quantity > 0 else 0,
                'total_price': cart_item.cart.get_total_price()  # Assuming a method for total cart price
            })
        return redirect('cart_management:cart_detail')
    except CartItem.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Item not found'}, status=404)
        return redirect('cart_management:cart_detail')


@login_required(login_url='accounts:user_login_view')
def remove_from_cart(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id)
    if cart_item.cart.user == request.user:
        cart_item.delete()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Item removed from cart'})
        return redirect('cart_detail')
    return JsonResponse({'error': 'You are not authorized to remove this item'}, status=403)
