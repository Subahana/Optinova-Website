from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Cart, CartItem, Wishlist, Coupon  # Ensure you have a Coupon model
from products.models import ProductVariant
from django.contrib import messages
from django.middleware.csrf import get_token
import json

# --------------Cart Management---------------#

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

        cart, _ = Cart.objects.get_or_create(user=user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)

        new_quantity = cart_item.quantity + quantity if not created else quantity

        if new_quantity > variant.stock:
            return JsonResponse({
                'message': f'Only {variant.stock - cart_item.quantity} units are left to add to the cart',
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
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)

        # Clear the coupon from the cart if no coupon is applied
        if not request.GET.get('apply_coupon'):
            cart.coupon = None
            cart.save()

        # Initialize totals
        original_total = 0  # Total of original prices
        offer_total = 0     # Total with offers applied
        final_total = 0     # Total after coupon discount

        # Calculate individual prices with offers if applicable
        cart_items_with_offers = []
        for item in cart_items:
            # Original price and offer price
            original_price = item.variant.price
            offer_price = item.variant.get_discounted_price() if item.variant.get_discounted_price() else original_price
            total_price_with_offer = offer_price * item.quantity

            # Update the totals
            original_total += original_price * item.quantity
            offer_total += total_price_with_offer

            # Add item data with prices to the list
            cart_items_with_offers.append({
                'item': item,
                'original_price': original_price,
                'offer_price': offer_price,
                'total_price_with_offer': total_price_with_offer,
            })

        # Handle coupon discount if a coupon is applied
        discount_amount = 0
        if cart.coupon:
            discount_amount = cart.coupon.get_discount_amount(offer_total)  # Apply discount on offer total

        # Final total after applying coupon discount
        final_total = offer_total - discount_amount
        total_items = sum(item.quantity for item in cart_items)

        # Get variants not in cart
        all_variants = ProductVariant.objects.all()
        in_cart_variants = cart_items.values_list('variant_id', flat=True)
        variants_not_in_cart = all_variants.exclude(id__in=in_cart_variants)

        context = {
            'cart_items': cart_items,
            'cart_items_with_offers': cart_items_with_offers,  # Pass updated list with offer-adjusted prices
            'original_total': original_total,                  # Total of original prices without any offers
            'offer_total': offer_total,                        # Total with offers applied
            'discount_amount': discount_amount,                # Discount amount from coupon
            'final_total': final_total,                        # Final price after coupon discount
            'variants_not_in_cart': variants_not_in_cart,
            'total_items': total_items,
            'csrf_token': get_token(request),
            'coupon_code': cart.coupon.code if cart.coupon else None  
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
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

            # Check stock availability
            available_stock = cart_item.variant.stock
            if new_quantity > available_stock:
                return JsonResponse({
                    'success': False,
                    'error': f"Only {available_stock} items available in stock."
                })

            # Update quantity if it’s valid
            if new_quantity > 0:
                cart_item.quantity = new_quantity
                cart_item.save()

                # Updated item price and cart totals
                item_total_price = cart_item.total_price()  # Uses the cart item’s quantity
                cart = cart_item.cart

                # Calculate original and discounted totals
                original_total = cart.get_original_total()
                discount_amount = cart.get_discount() if cart.coupon else 0
                new_total = original_total - discount_amount
                total_items = sum(item.quantity for item in cart.cartitem_set.all())

                return JsonResponse({
                    'success': True,
                    'item_quantity': cart_item.quantity,
                    'item_total_price': item_total_price,
                    'total_items': total_items,
                    'original_total': original_total,
                    'discount_amount': discount_amount,
                    'new_total': new_total
                })
            else:
                return JsonResponse({'success': False, 'error': 'Quantity must be at least 1.'})

        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cart item not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

# --------------Wishlist Management---------------#

@login_required(login_url='accounts:user_login_view')
def view_wishlist(request):
    wishlist = request.user.wishlist
    wishlist_items = wishlist.variants.all()

    context = {
        'wishlist_items': wishlist_items,
        'wishlist': wishlist,
        'csrf_token': get_token(request) 
    }
    return render(request, 'cart_management/wishlist.html', context)

@login_required(login_url='accounts:user_login_view')
def add_to_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    wishlist.variants.add(variant)
    return redirect('view_wishlist')

@login_required(login_url='accounts:user_login_view')
def remove_from_wishlist(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        selected_items = data.get('selected_items', [])

        if selected_items:
            wishlist = Wishlist.objects.get(user=request.user)
            for item_id in selected_items:
                variant = get_object_or_404(ProductVariant, id=item_id)
                wishlist.variants.remove(variant)

        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'error'}, status=400)
