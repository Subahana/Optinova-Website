from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/<int:id>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:id>/activate/', views.activate_category, name='activate_category'),
    path('categories/<int:id>/delete/', views.permanent_delete_category, name='permanent_delete_category'),
    path('categories/<int:id>/soft-delete/', views.soft_delete_category, name='soft_delete_category'),

    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:product_id>/soft-delete/', views.soft_delete_product, name='soft_delete_product'),
    path('products/<int:product_id>/activate/', views.activate_product, name='activate_product'),
    path('products/<int:product_id>/delete/', views.permanent_delete_product, name='permanent_delete_product'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/upload_images/', views.upload_product_image, name='upload_product_image'),
    path('products/product/<int:product_id>/delete_selected_images/', views.delete_selected_images, name='delete_selected_images'),


    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
]
