from django.urls import path
from . import views


urlpatterns = [
    path('', views.voter_login, name="voter_login"),
    path('administrator/login/', views.admin_login, name="account_login"),
    path('choose_election/', views.choose_election, name="choose_election"), # Keeping name account_login for admin convenience or changing? Let's check existing refs.
    # Existing refs use 'account_login'. If I change it, I must update all templates.
    # Let's keep 'account_login' for admin to minimize disruption, but the path is now specific.
    # Actually, voter login is the root index so maybe 'voter_login' is better.
    path('logout/', views.account_logout, name="account_logout"),
]
