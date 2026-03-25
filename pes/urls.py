from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# --- PŘIDÁNO PRO SITEMAPY ---
from django.contrib.sitemaps.views import sitemap
from home.sitemaps import StaticViewSitemap, PesSitemap
# Pokud už máš sitemaps i pro inzerci, přidej ji sem taky:
# from inzerce.sitemaps import InzeratSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'psi': PesSitemap,
    # 'inzerce': InzeratSitemap,
}
# ----------------------------

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('users/', include('users.urls')),
    path('inzerce/', include('inzerce.urls')),

    # --- CESTA PRO BING/GOOGLE ---
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)