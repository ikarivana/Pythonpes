from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('mapa/', views.mapa_sluzeb, name='mapa_sluzeb'),
    path('mapa/pridat/', views.pridat_sluzbu, name='pridat_sluzbu'),
    path('mapa/upravit/<int:pk>/', views.upravit_sluzbu, name='upravit_sluzbu'),
    path('mapa/smazat/<int:pk>/', views.smazat_sluzbu, name='smazat_sluzbu'),
    path('kontakt/', views.kontakt, name='kontakt'),
    path('podminky/', views.podminky, name='podminky'),
    path('cookies/', views.cookies, name='cookies'),
]