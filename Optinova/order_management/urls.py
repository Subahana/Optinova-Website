from django.urls import path
from .views import checkout, VerifyRazorpayPayment, cod_order_success,razorpay_order_success, order_failure, list_orders, update_order_status, cancel_order, return_order,complete_payment

urlpatterns = [
    path('checkout/', checkout, name='checkout'),
    path('order/success/razorpay/<str:razorpay_order_id>/', razorpay_order_success, name='razorpay_order_success'),
    path('order/success/cod/<int:order_id>/', cod_order_success, name='cod_order_success'),
    path('order_failure/<int:order_id>/', order_failure, name='order_failure'),
    path('complete_payment/<int:order_id>/',complete_payment, name='complete_payment'),
    path('list_orders/', list_orders, name='list_orders'),
    path('update_order_status/<int:order_id>/', update_order_status, name='update_order_status'),
    path('cancel_order/<int:order_id>/', cancel_order, name='cancel_order'),
    path('return_order/<int:order_id>/', return_order, name='return_order'),
    path('verify_razorpay_payment/', VerifyRazorpayPayment.as_view(), name='verify_razorpay_payment'),
]
