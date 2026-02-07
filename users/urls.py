from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- ZÁKLADNÍ SPRÁVA PSŮ ---
    path('seznam/', views.seznam_psu, name='seznam_psu'),
    path('pridat/', views.pridat_psa, name='pridat_psa'),
    path('upravit/<int:pk>/', views.upravit_psa, name='upravit_psa'),
    path('smazat/<int:pk>/', views.smazat_psa, name='smazat_psa'),
    path('terminy/', views.terminy, name='terminy'),
    path('ockovani/pridat/<int:pes_id>/', views.pridat_ockovani, name='pridat_ockovani'),

    # --- LOGIN / LOGOUT ---
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),

    # --- SOCIÁLNÍ SÍŤ (ROZCESTNÍK A PŘIDÁVÁNÍ) ---
    path('zdi/', views.seznam_zdi, name='seznam_zdi'),
    path('zdi/pridat/<str:typ_kategorie>/', views.pridat_polozku_vse, name='pridat_polozku'),

    # --- DETAIL ZDI A PŘÍSPĚVKY ---
    path('zed/<slug:slug>/', views.zed_plemene, name='zed_plemene'),
    path('prispevek/upravit/<int:pk>/', views.upravit_prispevek, name='upravit_prispevek'),
    path('prispevek/smazat/<int:pk>/', views.smazat_prispevek, name='smazat_prispevek'),

    # --- KOMENTÁŘE A ODPOVĚDI ---
    # Tyto dvě cesty jsou univerzální pro obojí (komentář i odpověď)
    path('komentar/smazat/<int:pk>/', views.smazat_komentar, name='smazat_komentar'),
    path('komentar/upravit/<int:pk>/', views.upravit_komentar, name='upravit_komentar'),
    # Tato cesta slouží k vytvoření nové odpovědi
    path('komentar/odpoved/<int:parent_id>/', views.pridat_odpoved, name='pridat_odpoved'),

    # --- PROFIL A INTERAKCE ---
    path('muj-profil/', views.profil_uzivatele, name='profil'),
    path('like/<int:post_id>/', views.pridej_like, name='like_post'),
]
