from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- ZÁKLADNÍ SPRÁVA PSŮ ---
    path('seznam/', views.seznam_psu, name='seznam_psu'),
    path('pridat/', views.pridat_psa, name='pridat_psa'),
    path('upravit/<int:pk>/', views.upravit_psa, name='upravit_psa'),
    path('smazat/<int:pk>/', views.smazat_psa, name='smazat_psa'),
    path('veterinar/', views.veterinar, name='veterinar'),
    path('ockovani/pridat/<int:pes_id>/', views.pridat_ockovani, name='pridat_ockovani'),
    path('moji-psi/', views.seznam_psu, name='seznam_psu'),

    # --- DETAIL A NOUZOVÝ SYSTÉM ---
    path('pes-detail/<int:pes_id>/', views.detail_psa, name='detail_psa'),
    path('pes/<int:pes_id>/', views.nouzovy_profil_psa, name='nouzovy_profil_psa'),
    path('pes/<int:pes_id>/odeslat-polohu/', views.odeslat_polohu_nalezu, name='odeslat_polohu'),
    path('pes/<int:pes_id>/odeslat-email/', views.odeslat_sos_email, name='odeslat_sos_email'),  # PŘIDÁNO
    path('pes/<int:pk>/prepnout-ztratu/', views.prepnout_ztratu, name='prepnout_ztratu'),

    # --- ZDRAVOTNÍ ZÁZNAMY ---
    path('zaznam/upravit/<int:pk>/', views.upravit_zaznam, name='upravit_zaznam'),
    path('zaznam/smazat/<int:pk>/', views.smazat_zaznam, name='smazat_zaznam'),

    # --- SPRÁVA GALERIE A ÚSPĚCHŮ ---
    path('pes/<int:pes_id>/galerie/pridat-foto/', views.pridat_foto, name='pridat_foto'),
    path('pes/<int:pes_id>/galerie/pridat-video/', views.pridat_video, name='pridat_video'),
    path('foto/smazat/<int:pk>/', views.smazat_foto, name='smazat_foto'),
    path('video/smazat/<int:pk>/', views.smazat_video, name='smazat_video'),
    path('pes/<int:pes_id>/uspech/pridat/', views.pridat_uspech, name='pridat_uspech'),
    path('pes/<int:pes_id>/pdf/', views.export_pes_pdf, name='export_pes_pdf'),

    # --- LOGIN / LOGOUT / REGISTRACE ---
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),

    # Obnova hesla
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='users/password_reset.html'),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
         name='password_reset_complete'),

    # --- SOCIÁLNÍ SÍŤ ---
    path('zdi/', views.seznam_zdi, name='seznam_zdi'),
    path('zdi/pridat/<str:typ_kategorie>/', views.pridat_polozku_vse, name='pridat_polozku'),
    path('zed/<slug:slug>/', views.zed_plemene, name='zed_plemene'),
    path('prispevek/upravit/<int:pk>/', views.upravit_prispevek, name='upravit_prispevek'),
    path('prispevek/smazat/<int:pk>/', views.smazat_prispevek, name='smazat_prispevek'),

    # --- KOMENTÁŘE ---
    path('komentar/smazat/<int:pk>/', views.smazat_komentar, name='smazat_komentar'),
    path('komentar/upravit/<int:pk>/', views.upravit_komentar, name='upravit_komentar'),
    path('komentar/odpoved/<int:parent_id>/', views.pridat_odpoved, name='pridat_odpoved'),

    # --- PROFIL A NOTIFIKACE ---
    path('muj-profil/', views.profil_uzivatele, name='profil'),
    path('profil/upravit/', views.upravit_profil, name='upravit_profil'),
    path('like/<int:post_id>/', views.pridej_like, name='like_post'),
    path('notifikace/', views.seznam_notifikaci, name='seznam_notifikaci'),
]