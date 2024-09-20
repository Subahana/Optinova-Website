from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('order_success/<int:order_id>/', views.order_success, name='order_success'),
    path('list_orders/', views.list_orders, name='list_orders'),
    path('orders/update/<int:order_id>/', views.update_order_status, name='update_order_status'),  
    path('orders/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'), 
]
