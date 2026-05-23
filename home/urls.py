from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

urlpatterns = [
    # Hlavní stránka
    path('', views.index, name='home'),

    # Blog cesty
    path('blog/', views.blog_seznam, name='blog_seznam'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    # Formuláře pro správu:
    path('blog/novy/pridat/', views.clanek_vytvor, name='clanek_vytvor'),
    path('blog/<slug:slug>/upravit/', views.clanek_uprav, name='clanek_uprav'),
    path('blog/<slug:slug>/smazat/', views.clanek_smaz, name='clanek_smaz'),
    path('komentar/upravit/<int:pk>/', views.upravit_komentar, name='upravit_komentar'),
    path('komentar/smazat/<int:pk>/', views.smazat_komentar, name='smazat_komentar'),

    # --- MAPA A SLUŽBY ---
    path('mapa/', views.mapa_sluzeb, name='mapa_sluzeb'),
    path('mapa/pridat/', views.pridat_sluzbu, name='pridat_sluzbu'),
    path('mapa/upravit/<int:pk>/', views.upravit_sluzbu, name='upravit_sluzbu'),
    path('mapa/smazat/<int:pk>/', views.smazat_sluzbu, name='smazat_sluzbu'),
    path('detail-sluzby/<int:pk>/', views.detail_sluzby, name='detail_sluzby'),
    path('sluzba/<int:pk>/recenze/', views.pridat_recenzi, name='pridat_recenzi'),
    path('recenze/upravit/<int:pk>/', views.upravit_recenzi, name='upravit_recenzi'),
    path('recenze/smazat/<int:pk>/', views.smazat_recenzi, name='smazat_recenzi'),

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

  # --- INTEGRACE / PLATBY ---
    path('webhook/simpleshop/', views.simpleshop_webhook, name='simpleshop_webhook'),
    path('dekujeme-za-nakup/', views.dekujeme_za_nakup, name='dekujeme_za_nakup'),
    path('dekujeme-za-znamku/', views.dekujeme_za_znamku, name='dekujeme_za_znamku'),
]

# --- PODPORA PRO NAHRANÉ OBRÁZKY (MEDIA MÁGIE) ---
# Pokud běžíte v DEBUG režimu (na localhostu), Django bude servírovat obrázky článků a mazlíčků automaty.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

