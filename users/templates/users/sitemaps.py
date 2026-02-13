from django.contrib.sitemaps import Sitemap
from .models import Pes

class PesSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Pes.objects.all()

    def lastmod(self, obj):
        # Pokud máš u Psa pole s datem aktualizace, dej ho sem
        return None