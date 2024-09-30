from django.shortcuts import get_object_or_404, redirect,render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Cart, CartItem , Wishlist
from products.models import Product,ProductVariant
from django.contrib import messages
from .models import CartItem
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

        # Retrieve the variant and user information
        variant = get_object_or_404(ProductVariant, id=variant_id)
        user = request.user  

        # Check if the item is out of stock
        if variant.stock <= 0:
            return JsonResponse({'message': 'Out of stock', 'status': 'error'})

        # Retrieve or create the user's cart and the corresponding cart item
        cart, _ = Cart.objects.get_or_create(user=user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)

        # If the cart item already exists, calculate the new total quantity
        new_quantity = cart_item.quantity + quantity if not created else quantity

        # Validate stock availability
        if new_quantity > variant.stock:
            return JsonResponse({
                'message': f'Only {variant.stock - cart_item.quantity} units are left to add to the cart',
                'status': 'error'
            })

        # Validate the maximum allowed quantity per item (e.g., 10 units)
        if new_quantity > 10:
            return JsonResponse({
                'message': 'You cannot add more than 10 units of this item',
                'status': 'error'
            })

        # Update the cart item quantity and save it
        cart_item.quantity = new_quantity
        cart_item.save()

        # Return a success response to indicate the item was successfully added
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
            # Retrieve the new quantity from the request
            new_quantity = int(request.POST.get('quantity'))
            cart_item = CartItem.objects.get(id=item_id)

            # Check if new quantity is greater than available stock
            available_stock = cart_item.variant.stock 
            if new_quantity > available_stock:
                return JsonResponse({
                    'success': False,
                    'error': f"Only {available_stock} items available in stock."
                })

            if new_quantity > 0:
                # Update the quantity of the cart item
                cart_item.quantity = new_quantity
                cart_item.save()

                # Calculate the total price for the updated quantity
                item_total_price = cart_item.quantity * cart_item.variant.price
                cart = cart_item.cart

                # Ensure the Cart model has a method to calculate the total price
                cart_total_price = cart.get_total_price()

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


# --------------Wishlist Management---------------#


@login_required(login_url='accounts:user_login_view')
def view_wishlist(request):
    wishlist = request.user.wishlist  # Adjust this if your wishlist logic is different
    wishlist_items = wishlist.variants.all()  # Adjust according to your model structure

    context = {
        'wishlist_items': wishlist_items,
        'wishlist': wishlist,
        'csrf_token': get_token(request) 

    }
    return render(request, 'cart_management/wishlist.html', context)

# Add to Wishlist
def add_to_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    wishlist.variants.add(variant)
    return redirect('view_wishlist')


def remove_from_wishlist(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        selected_items = data.get('selected_items', [])

        if selected_items:
            wishlist = Wishlist.objects.get(user=request.user)
            for item_id in selected_items:
                variant = get_object_or_404(ProductVariant, id=item_id)
                wishlist.variants.remove(variant)  # Remove selected variants from wishlist

        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'error'}, status=400)
