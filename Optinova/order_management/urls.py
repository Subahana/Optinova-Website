from django.urls import path
from . import views

urlpatterns = [
    # Checkout process
    path('checkout/', views.checkout, name='checkout'),    
    path('verify_razorpay_payment/', views.verify_razorpay_payment, name='verify_razorpay_payment'),    
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),    
    path('orders/', views.list_orders, name='list_orders'),   
    path('update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),    
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),    
    path('return-order/<int:order_id>/', views.return_order, name='return_order'),
]
