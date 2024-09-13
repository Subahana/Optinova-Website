from django.shortcuts import get_object_or_404, redirect,render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Cart, CartItem
from products.models import ProductVariant
from django.contrib import messages
from .models import CartItem
from django.middleware.csrf import get_token
import json

@login_required(login_url='accounts:user_login_view')
def add_to_cart(request, variant_id):
    if request.method == "POST":
        quantity = request.POST.get('quantity')

        try:
            quantity = int(quantity)
            if quantity <= 0:
                return JsonResponse({'message': 'Quantity must be greater than 0', 'status': 'error'})
        except ValueError:
            return JsonResponse({'message': 'Invalid quantity', 'status': 'error'})

        variant = get_object_or_404(ProductVariant, id=variant_id)
        user = request.user  
        if variant.stock <= 0:
            return JsonResponse({'message': 'Out of stock', 'status': 'error'})

        cart, created = Cart.objects.get_or_create(user=user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
        new_quantity = cart_item.quantity + quantity if not created else quantity

        if new_quantity > variant.stock:
            return JsonResponse({
                'message': f'Only {variant.stock - cart_item.quantity} units are left to Add in Cart',
                'status': 'error'
            })

        if new_quantity > 10:
            return JsonResponse({
                'message': 'You cannot add more than 10 units of this item',
                'status': 'error'
            })

        cart_item.quantity = new_quantity
        cart_item.save()

        return JsonResponse({'message': 'Item added to cart successfully', 'status': 'success'})
    else:
        return JsonResponse({'message': 'Invalid request method', 'status': 'error'})


@login_required(login_url='accounts:user_login_view')
def cart_detail(request):
    try:
        # Get or create the cart for the user
        cart, created = Cart.objects.get_or_create(user=request.user)

        # Fetch all cart items for the cart
        cart_items = CartItem.objects.filter(cart=cart)

        # Calculate total price and total items
        total_price = sum(item.total_price() for item in cart_items)
        total_items = sum(item.quantity for item in cart_items)  # Sum of all item quantities

        # Get all product variants and those not in the cart
        all_variants = ProductVariant.objects.all()
        in_cart_variants = cart_items.values_list('variant_id', flat=True)
        variants_not_in_cart = all_variants.exclude(id__in=in_cart_variants)

        context = {
            'cart_items': cart_items,
            'total_price': total_price,
            'variants_not_in_cart': variants_not_in_cart,
            'total_items': total_items,
            'csrf_token': get_token(request)  # Ensure this matches your frontend
        }

        return render(request, 'cart_management/cart_detail.html', context)
    except Exception as e:
        import traceback
        error_message = traceback.format_exc()
        print(f"Error in cart_detail view: {error_message}")
        return JsonResponse({'error': 'An error occurred.'}, status=500)


@login_required(login_url='accounts:user_login_view')
def remove_from_cart(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id)
    if cart_item.cart.user == request.user:
        cart_item.delete()
        return redirect('cart_detail')
    return JsonResponse({'error': 'You are not authorized to remove this item'}, status=403)


@login_required(login_url='accounts:user_login_view')
def update_cart_item_quantity(request, item_id):
    if request.method == 'POST':
        try:
            new_quantity = int(request.POST.get('quantity'))
            cart_item = CartItem.objects.get(id=item_id)

            # Check if new quantity is greater than available stock
            available_stock = cart_item.variant.stock  # Assuming 'stock' field exists in ProductVariant model
            if new_quantity > available_stock:
                return JsonResponse({
                    'success': False,
                    'error': f"Only {available_stock} items available in stock."
                })

            if new_quantity > 0:
                cart_item.quantity = new_quantity
                cart_item.save()

                item_total_price = cart_item.quantity * cart_item.variant.price
                cart = cart_item.cart
                cart_total_price = cart.get_total_price()  # Ensure this method exists in Cart model
                
                return JsonResponse({
                    'success': True,
                    'item_quantity': cart_item.quantity,
                    'item_total': item_total_price,
                    'cart_total': cart_total_price
                })
            else:
                return JsonResponse({'success': False, 'error': 'Quantity must be at least 1.'})
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cart item not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})
