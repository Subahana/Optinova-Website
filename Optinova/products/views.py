from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from django.contrib import messages
from .forms import *
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.urls import reverse

# Define the custom login URL

@login_required(login_url='accounts:admin_login')  
@never_cache
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'products/category_list.html', {'categories': categories})

@login_required(login_url='accounts:admin_login')  
@never_cache
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

@login_required(login_url='accounts:admin_login')  
@never_cache
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

@login_required(login_url='accounts:admin_login')  
@never_cache
def activate_category(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == "POST":
        category.is_active = True
        category.save()
        messages.success(request, 'Category activated successfully.')
    return redirect('category_list')

@login_required(login_url='accounts:admin_login')  
@never_cache
def permanent_delete_category(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == "POST":
        category.delete()
        messages.success(request, 'Category deleted permanently.')
    return redirect('category_list')

@login_required(login_url='accounts:admin_login')  
@never_cache
def soft_delete_category(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == "POST":
        category.is_active = False
        category.save()
        messages.success(request, 'Category deactivated successfully.')
    return redirect('category_list')

@login_required(login_url='accounts:admin_login')  
@never_cache
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
        if product_form.is_valid():
            product = product_form.save()
            return redirect('add_variant', product_id=product.id)
    else:
        product_form = ProductForm()

    return render(request, 'products/product_add.html', {'product_form': product_form})


@login_required(login_url='accounts:admin_login')
@never_cache
def add_variant(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        variant_form = ProductVariantForm(request.POST)
        print("Form Data:", request.POST)

        if variant_form.is_valid():
            print("Form Data:", request.POST)

            variant = variant_form.save(commit=False)
            variant.product = product  # Set the product
            variant.save()  # Save the variant
            print("Variant saved:", variant)  # Debugging: Confirm that the variant is saved

            return redirect('add_images', variant_id=variant.id)
        else:
            print(variant_form.errors)  # Print form errors for debugging
    else:
        variant_form = ProductVariantForm()

    return render(request, 'products/add_variant.html', {
        'product': product,
        'variant_form': variant_form,
    })


@login_required(login_url='accounts:admin_login')
@never_cache
def add_images(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product = variant.product
    
    if request.method == 'POST':
        image_formset = ProductImageFormSet(request.POST, request.FILES)
        if image_formset.is_valid():
            images = image_formset.save(commit=False)
            for image in images:
                image.variant = variant
                image.save()
            return redirect(reverse('product_detail', args=[product.id, variant.id]))
        else:
            print(image_formset.errors)
    else:
        image_formset = ProductImageFormSet(queryset=ProductImage.objects.none())
    
    return render(request, 'products/add_images.html', {
        'variant': variant,
        'image_formset': image_formset
    })



@login_required(login_url='accounts:admin_login')  
@never_cache
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES, instance=product)
        if product_form.is_valid():
            updated_product = product_form.save(commit=False)
            # Ensure that active products do not become inactive
            if product.is_active:
                updated_product.is_active = True
            else:
                updated_product.is_active = product.is_active  # Preserve the current 'is_active' status if it was inactive
            updated_product.save()
            messages.success(request, 'Product updated successfully.')
            return redirect('product_list')
    else:
        product_form = ProductForm(instance=product)

    return render(request, 'products/product_edit.html', {'product_form': product_form, 'product': product})


@login_required(login_url='accounts:admin_login')  
@never_cache
def soft_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = False
    product.save()
    messages.success(request, 'Product deactivated successfully!')
    return redirect('product_list')

@login_required(login_url='accounts:admin_login')  
@never_cache
def permanent_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        product.delete()
        messages.success(request, 'Product deleted permanently.')
    return redirect('product_list')

@login_required(login_url='accounts:admin_login')  
@never_cache
def activate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = True
    product.save()
    messages.success(request, 'Product activated successfully!')
    return redirect('product_list')

@login_required(login_url='accounts:admin_login')
@never_cache
def product_detail(request, product_id, variant_id):
    product = get_object_or_404(Product, id=product_id)
    variant = get_object_or_404(ProductVariant, id=variant_id)
    return render(request, 'products/product_detail.html', {'product': product, 'variant': variant})


@login_required(login_url='accounts:admin_login')
@never_cache
def delete_selected_images(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    if request.method == "POST":
        image_ids = request.POST.getlist('images_to_delete')
        if image_ids:
            # Delete images related to the specific variant
            ProductImage.objects.filter(id__in=image_ids, variant=variant).delete()
            messages.success(request, 'Selected images deleted successfully.')
        else:
            messages.warning(request, 'No images were selected for deletion.')
    
    # Redirect to the product detail page
    return redirect(reverse('product_detail', args=[variant.id]))

@login_required(login_url='accounts:admin_login')  
@never_cache
def admin_dashboard(request):
    return redirect('admin_page')
