from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from . import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(('accounts.urls', 'accounts'), namespace='accounts')), 
    path('accounts/', include('allauth.urls')),  
    path('', include('django.contrib.auth.urls')),
    path('admin_page/', include('admin_page.urls')),
    path('user_home/', include('user_home.urls')),
    path('products/', include('products.urls')),
    path('user_profile/', include('user_profile.urls')),
    path('cart_management/', include('cart_management.urls')),  
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

