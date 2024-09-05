from django.urls import path
from .views import *

urlpatterns = [
    path('categories/', category_list, name='category_list'),
    path('categories/add/', add_category, name='add_category'),
    path('categories/edit/<int:id>/', edit_category, name='edit_category'),
    path('categories/activate/<int:id>/', activate_category, name='activate_category'),
    path('categories/delete/permanent/<int:id>/', permanent_delete_category, name='permanent_delete_category'),
    path('categories/delete/soft/<int:id>/', soft_delete_category, name='soft_delete_category'),

    path('products/', product_list, name='product_list'),
    path('products/add/', add_product, name='add_product'),
    path('products/variants/<int:product_id>/', add_variant, name='add_variant'),
    path('products/images/<int:variant_id>/', add_images, name='add_images'),
    path('products/edit/<int:product_id>/', edit_product, name='edit_product'),
    path('products/delete/soft/<int:product_id>/', soft_delete_product, name='soft_delete_product'),
    path('products/images/delete/<int:variant_id>/', delete_selected_images, name='delete_selected_images'),
    path('products/activate/<int:product_id>/', activate_product, name='activate_product'),
    path('products/detail/<int:product_id>/<int:variant_id>/', product_detail, name='product_detail'),

    path('images/delete/<int:product_id>/', delete_selected_images, name='delete_selected_images'),

    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),
]
