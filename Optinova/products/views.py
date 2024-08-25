from django.shortcuts import render, redirect, get_object_or_404
from .models import Category, Product, ProductImage
from django.contrib import messages
from .forms import CategoryForm, ProductForm,ProductImageForm
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
@never_cache
def add_product(request):
    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES)
        if product_form.is_valid():
            # Save the new product instance with is_active set to True
            new_product = product_form.save(commit=False)
            new_product.is_active = True  # Set the product to be active
            new_product.save()
            messages.success(request, 'Product added successfully.')
            return redirect('product_list')
    else:
        product_form = ProductForm()
        
    return render(request, 'products/product_add.html', {'product_form': product_form})


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
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'products/product_detail.html', {'product': product})


@login_required(login_url='accounts:admin_login')  
@never_cache
def upload_product_image(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductImageForm(request.POST, request.FILES)
        if form.is_valid():
            product_image = form.save(commit=False)
            product_image.product = product
            product_image.save()
            messages.success(request, 'Image uploaded successfully!')
            return redirect('product_detail', product_id=product.id)
        else:
            print(form.errors) 
    else:
        form = ProductImageForm()
    return render(request, 'products/upload_product_image.html', {'form': form, 'product': product})

@login_required(login_url='accounts:admin_login')  
@never_cache
def delete_selected_images(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        image_ids = request.POST.getlist('images_to_delete')
        if image_ids:
            ProductImage.objects.filter(id__in=image_ids).delete()
            messages.success(request, 'Selected images deleted successfully.')
        else:
            messages.warning(request, 'No images were selected for deletion.')
    return redirect('product_detail', product_id=product.id)


@login_required(login_url='accounts:admin_login')  
@never_cache
def admin_dashboard(request):
    return redirect('admin_page')
