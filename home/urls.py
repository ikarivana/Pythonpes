from django.urls import path
from . import views
from .views import simpleshop_webhook

urlpatterns = [
    # Hlavní stránka
    path('', views.index, name='home'),

    # --- MAPA A SLUŽBY ---
    path('mapa/', views.mapa_sluzeb, name='mapa_sluzeb'),
    path('mapa/pridat/', views.pridat_sluzbu, name='pridat_sluzbu'),
    path('mapa/upravit/<int:pk>/', views.upravit_sluzbu, name='upravit_sluzbu'),
    path('mapa/smazat/<int:pk>/', views.smazat_sluzbu, name='smazat_sluzbu'),
    path('detail-sluzby/<int:pk>/', views.detail_sluzby, name='detail_sluzby'),
    path('sluzba/<int:pk>/recenze/', views.pridat_recenzi, name='pridat_recenzi'),

    # Komunitní tlačítka na mapě (pro Nebezpečí)
    path('mapa/nahlasit-neaktualni/<int:id>/', views.nahlasit_neaktualni, name='nahlasit_neaktualni'),
    path('mapa/stale-aktualni/<int:id>/', views.stale_aktualni, name='stale_aktualni'),

    # --- OSTATNÍ STRÁNKY ---
    path('kontakt/', views.kontakt, name='kontakt'),
    path('podminky/', views.podminky, name='podminky'),
    path('cookies/', views.cookies, name='cookies'),
    path('gdpr/', views.gdpr, name='gdpr'),
    path('cenik/', views.cenik, name='cenik'),
    path('pruvodce/', views.pruvodce, name='pruvodce'),

    path('webhook/simpleshop/', views.simpleshop_webhook, name='simpleshop_webhook'),
    path('dekujeme-za-nakup/', views.dekujeme_za_nakup, name='dekujeme_za_nakup'),
    path('dekujeme-za-znamku/', views.dekujeme_za_znamku, name='dekujeme_za_znamku'),
]