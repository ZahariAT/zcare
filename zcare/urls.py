"""
URL configuration for zcare project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt import views as jwt_views

from item import views
from core import views as core_views

api_prefix = 'api'

router = routers.DefaultRouter()
router.register(r'items', views.ItemViewSet, basename='item')
router.register(r'categories', views.CategoryViewSet, basename='category')

urlpatterns = [
    path('admin/', admin.site.urls),
    path(f'{api_prefix}/', include(router.urls)),
    path(f'{api_prefix}/register/', core_views.RegisterUserView.as_view(), name='register'),
    path(f'{api_prefix}/activate/<token>', core_views.ActivateUserView.as_view(), name='activate-user'),
    path(f'{api_prefix}/login/', core_views.LoginUserView.as_view(), name='login'),
    path(f'{api_prefix}/token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path(f'{api_prefix}/logout/', core_views.LogoutUserView.as_view(), name='logout'),
    path(f'{api_prefix}/user/delete/', core_views.DeleteAccountView.as_view(), name='delete-user'),
    path(f'{api_prefix}/user/order_history', views.OrderHistoryView.as_view(), name='order-history'),
    path(f'{api_prefix}/items/<int:pk>/buy', views.item_buy, name='item-buy'),
    path(f'{api_prefix}/search/', views.CorrectedItemSearchView.as_view(), name='item-search'),
    path(f'{api_prefix}/business-statistics/', views.BusinessStatisticsView.as_view(), name='business-statistics'),
]
