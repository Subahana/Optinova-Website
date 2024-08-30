from django.urls import path
from . import views

urlpatterns = [
    path('user_profile', views.user_profile, name='user_profile'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('edit_profile_pic/', views.edit_profile_pic, name='edit_profile_pic'),
    path('change_password/', views.change_password, name='change_password'),
    path('add_address/', views.add_address, name='add_address'),  
    path('edit_address/', views.edit_address, name='edit_address'),
    path('delete_address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('edit_address/<int:address_id>/', views.edit_address, name='edit_address'),
    path('cancel_order/<int:order_id>/', views.cancel_order, name='cancel_order'),
]
