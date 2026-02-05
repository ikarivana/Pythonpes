from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('seznam/', views.seznam_psu, name='seznam_psu'),
    path('pridat/', views.pridat_psa, name='pridat_psa'),
    path('upravit/<int:pk>/', views.upravit_psa, name='upravit_psa'),
    path('smazat/<int:pk>/', views.smazat_psa, name='smazat_psa'),
    path('terminy/', views.terminy, name='terminy'),

    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
]