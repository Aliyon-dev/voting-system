from django.urls import path
from . import api_views

urlpatterns = [
    path('login/', api_views.api_login, name='api_login'),
    path('register/', api_views.api_register, name='api_register'),
    path('logout/', api_views.api_logout, name='api_logout'),
    path('profile/', api_views.api_user_profile, name='api_user_profile'),
]


