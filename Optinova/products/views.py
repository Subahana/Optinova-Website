from django.shortcuts import render, redirect, get_object_or_404
from .models import Product,ProductVariant,ProductImage,Category
from django.contrib import messages
from .forms import ProductForm,CategoryForm,ProductImageForm,ProductImageFormSet,ProductVariantForm
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
import base64
from django.core.files.base import ContentFile
import logging
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import render, get_object_or_404, redirect
from django.forms import modelformset_factory


logger = logging.getLogger(__name__)

        #   category_listt   
@login_required(login_url='accounts:admin_login')  
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'products/category_list.html', {'categories': categories})

        #    add_category
@login_required(login_url='accounts:admin_login')  
def add_category(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category added successfully.')
            return redirect('category_list')    
    else:
        form = CategoryForm()   
    return render(request, 'products/category_add_form.html', {'form': form})

          #   edit_category      
@login_required(login_url='accounts:admin_login')  
def edit_category(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully.')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'products/category_edit_form.html', {'form': form})

         #    activate_category
@login_required(login_url='accounts:admin_login')  
def activate_category(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == "POST":
        category.is_active = True
        category.save()
        messages.success(request, 'Category activated successfully.')
    return redirect('category_list')

        #  permanent_delete_category
@login_required(login_url='accounts:admin_login')  
def permanent_delete_category(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == "POST":
        category.delete()
        messages.success(request, 'Category deleted permanently.')
    return redirect('category_list')

        #   Deactivating Category
@login_required(login_url='accounts:admin_login')  
def soft_delete_category(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == "POST":
        category.is_active = False
        category.save()
        messages.success(request, 'Category deactivated successfully.')
    return redirect('category_list')

@login_required(login_url='accounts:admin_login')  
def product_list(request):
    categories = Category.objects.filter(is_active=True)
    
    # Initial product query with only active categories
    products = Product.objects.filter(
        category__is_active=True  # Ensure the product's category is active
    )
    
    show_inactive = request.GET.get('show_inactive')
    if show_inactive:
        products = Product.objects.all()  # Include all products if show_inactive is set
    else:
        products = products.filter(is_active=True)  # Filter active products

    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    context = {
        'categories': categories,
        'products': products,
        'show_inactive': show_inactive,
    }
    return render(request, 'products/product_list.html', context)


@login_required(login_url='accounts:admin_login')
def add_product(request):
    if request.method == 'POST':
        product_form = ProductForm(request.POST)
        if product_form.is_valid() :
            product = product_form.save()
            return redirect('add_variant', product_id=product.id)
    else:
        product_form = ProductForm()

    return render(request, 'products/product_add.html', {'product_form': product_form})


@login_required(login_url='accounts:admin_login')
def add_variant(request, product_id):
    product = get_object_or_404(Product, id=product_id)  # Get the product by its ID
    
    if request.method == 'POST':
        variant_form = ProductVariantForm(request.POST, product=product)
        if variant_form.is_valid():            
            variant = variant_form.save(commit=False)
            variant.product = product 
            variant.save()             
            return redirect('add_images', variant_id=variant.id)
        else:
            print(variant_form.errors)
    else:
        variant_form = ProductVariantForm(product=product)
    return render(request, 'products/add_variant.html', {
        'product': product,
        'variant_form': variant_form,
        'csrf_token': get_token(request)

    })


@login_required(login_url='accounts:admin_login')
def add_images(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    # Handle GET request to render the image upload form
    if request.method == 'GET':
        return render(request, 'products/add_images.html', {'variant': variant})

    
    # Handle POST request to process the image upload
    if request.method == 'POST':
        cropped_image_data = request.POST.get('croppedImageData')

        if cropped_image_data:
            format, imgstr = cropped_image_data.split(';base64,')
            ext = format.split('/')[-1]
            image_data = ContentFile(base64.b64decode(imgstr), name=f'cropped_image.{ext}')
            
            product_image = ProductImage(variant=variant, image=image_data)
            product_image.save()
            return JsonResponse({'success': True})

    return JsonResponse({'success': False}, status=400)


@login_required(login_url='accounts:admin_login')  
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES, instance=product)
        if product_form.is_valid():
            updated_product = product_form.save(commit=False)
            updated_product.is_active = product.is_active
            updated_product.save()
            messages.success(request, 'Product updated successfully.')
            return redirect('product_list')
        else:
            # Debugging: Print form errors to console
            print(product_form.errors)  # Check why form validation is failing
    else:
        product_form = ProductForm(instance=product)

    return render(request, 'products/product_edit.html', {'product_form': product_form, 'product': product})


@login_required(login_url='accounts:admin_login')
def edit_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product = variant.product

    if request.method == 'POST':
        variant_form = ProductVariantForm(request.POST, instance=variant, product=product)  # Pass the instance
        if variant_form.is_valid():
            updated_variant = variant_form.save(commit=False)
            updated_variant.product = product  
            updated_variant.save()
            messages.success(request, 'Variant updated successfully.')
            return redirect('edit_images', variant_id=variant.id)
        else:
            messages.error(request, 'There was an error updating the variant. Please check the form.')
    else:
        variant_form = ProductVariantForm(instance=variant, product=product)  # Pass the instance here too
    
    return render(request, 'products/edit_variant.html', {
        'product': product,
        'variant_form': variant_form,
        'variant_color': variant.color,  # Pass color separately
    })



@login_required(login_url='accounts:admin_login')
def edit_images(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    # Prepopulate the formset with existing images
    image_formset = ProductImageFormSet(queryset=variant.images.all())

    if request.method == 'POST':
        # Bind formset with POST data and files
        image_formset = ProductImageFormSet(request.POST, request.FILES, queryset=variant.images.all())
        
        if image_formset.is_valid():
            # Save new images and handle deletions
            instances = image_formset.save(commit=False)
            for instance in instances:
                if instance.image:  # Check if a new image was uploaded
                    instance.variant = variant
                    instance.save()
                else:
                    # If no new image is uploaded, keep existing
                    instance.save()  # This retains the existing image in the DB

            # Handle deletions
            for obj in image_formset.deleted_objects:
                obj.delete()

            messages.success(request, 'Images updated successfully.')
            return redirect('edit_images', variant_id=variant.id)

    return render(request, 'products/edit_images.html', {
        'variant': variant,
        'image_formset': image_formset,
    })


@login_required(login_url='accounts:admin_login')
@require_POST
def soft_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = False
    product.save()
    messages.success(request, 'Product deactivated successfully.')
    return redirect('product_list')

@login_required(login_url='accounts:admin_login')
@require_POST
def activate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = True
    product.save()
    messages.success(request, 'Product activated successfully.')
    return redirect('product_list')

@login_required(login_url='accounts:admin_login')
@require_POST
def permanent_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)    
    product.delete()    
    messages.success(request, 'Product deleted permanently.')    
    return redirect('product_list')

@login_required(login_url='accounts:admin_login')
@require_POST
def activate_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    variant.is_active = True  # Activate the variant
    variant.save()
    messages.success(request, 'Variant activated successfully.')
    return redirect(reverse('product_detail', args=[variant.product.id, variant.id]))

@login_required(login_url='accounts:admin_login')
@require_POST
def deactivate_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    variant.is_active = False  # Deactivate the variant
    variant.save()
    messages.success(request, 'Variant deactivated successfully.')
    
    # Make sure both product_id and variant_id are passed correctly
    return redirect(reverse('product_detail', args=[variant.product.id, variant.id]))


@login_required(login_url='accounts:admin_login')
@require_POST
def delete_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product_id = variant.product.id  # Store product ID before deleting
    variant.delete()  # Permanently delete the variant
    messages.success(request, 'Variant deleted permanently.')
    return redirect('product_detail', product_id=product_id, variant_id=variant_id)


@login_required(login_url='accounts:admin_login')
def product_detail(request, product_id, variant_id=None):
    # Get the product
    product = get_object_or_404(Product, id=product_id)

    # Check if the product has active variants
    variants = product.variants.filter(is_active=True)
    # Handle the case where there are no active variants
    if not variants.exists():
        # No active variants, render the product details with a message or without variant info
        return render(request, 'products/product_detail.html', {
            'product': product,
            'variant': None,
            'error': 'No variants available for this product.'
        })

    # If a specific variant is requested, try to fetch it
    if variant_id:
        try:
            variant = variants.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            # If the variant doesn't exist, fallback to the first available variant
            variant = variants.first()
            # Redirect to the product detail page with the first available variant
            return redirect('product_detail', product_id=product_id, variant_id=variant.id)
    else:
        # If no variant_id is provided, use the first available variant
        variant = variants.first()

    return render(request, 'products/product_detail.html', {
        'product': product,
        'variant': variant,
    })


@login_required(login_url='accounts:admin_login')
def delete_selected_images(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    if request.method == "POST":
        image_ids = request.POST.getlist('images_to_delete')
        if image_ids:
            ProductImage.objects.filter(id__in=image_ids, variant=variant).delete()
            messages.success(request, 'Selected images deleted successfully.')
        else:
            messages.warning(request, 'No images were selected for deletion.')
    
    # Pass both product_id and variant_id to reverse()
    return redirect(reverse('product_detail', args=[variant.product.id, variant.id]))

@login_required(login_url='accounts:admin_login')  
@never_cache
def admin_dashboard(request):
    return redirect('admin_page')
