from django.urls import path
from . import views

urlpatterns = [
    # Hlavní stránka
    path('', views.index, name='home'),

    # Mapa a služby
    path('mapa/', views.mapa_sluzeb, name='mapa_sluzeb'),
    path('mapa/pridat/', views.pridat_sluzbu, name='pridat_sluzbu'),
    path('mapa/upravit/<int:pk>/', views.upravit_sluzbu, name='upravit_sluzbu'),
    path('mapa/smazat/<int:pk>/', views.smazat_sluzbu, name='smazat_sluzbu'),

    # Komunitní tlačítka na mapě (pro Nebezpečí)
    path('mapa/nahlasit-neaktualni/<int:id>/', views.nahlasit_neaktualni, name='nahlasit_neaktualni'),
    path('mapa/stale-aktualni/<int:id>/', views.stale_aktualni, name='stale_aktualni'),

    # Ostatní stránky
    path('kontakt/', views.kontakt, name='kontakt'),
    path('podminky/', views.podminky, name='podminky'),
    path('cookies/', views.cookies, name='cookies'),
    path('cenik/', views.cenik, name='cenik'),
]
