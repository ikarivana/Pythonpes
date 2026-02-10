from django.urls import path
from . import views

urlpatterns = [
    path('', views.seznam_inzeratu, name='seznam_inzeratu'),
    path('pridat/', views.pridat_inzerat, name='pridat_inzerat'),
    path('detail/<int:pk>/', views.detail_inzeratu, name='detail_inzeratu'),
    path('upravit/<int:pk>/', views.upravit_inzerat, name='upravit_inzerat'),
    path('smazat/<int:pk>/', views.smazat_inzerat, name='smazat_inzerat'),
]