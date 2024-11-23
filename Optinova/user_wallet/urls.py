from django.urls import path
from . import views

urlpatterns = [
    path('wallet/', views.wallet, name='wallet'),
    path('wallet/add_funds/', views.add_funds, name='add_funds'),
    path('wallet/wallet_payment/', views.wallet_payment, name='wallet_payment'),

]
