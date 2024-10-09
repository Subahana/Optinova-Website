from django.urls import path
from . import views

urlpatterns = [
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/create/', views.create_coupon, name='create_coupon'),
    path('coupons/edit/<int:coupon_id>/', views.edit_coupon, name='edit_coupon'),
]
