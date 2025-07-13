from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.login, name='api_login'),
    path('auth/logout/', views.logout, name='api_logout'),
    path('auth/user/', views.user_info, name='api_user_info'),
]