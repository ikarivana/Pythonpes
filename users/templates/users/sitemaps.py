from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from users.models import Pes


class PesSitemap(Sitemap):
    # Jak často se profily mění (u deníků je daily ideální)
    changefreq = "daily"
    # Vysoká priorita pro profily mazlíčků
    priority = 0.9

    def items(self):
        # Indexujeme jen veřejné profily (pokud máš nějaké pole 'soukromy')
        # A seřadíme je od nejnovějších
        return Pes.objects.all().order_by('-id')

    def lastmod(self, obj):
        # Tady je kritické mít v modelu Pes pole např. 'upraveno = models.DateTimeField(auto_now=True)'
        # Pokud ho nemáš, doporučuji ho přidat. Zatím vracíme aspoň něco:
        try:
            return obj.updated_at # nebo jiný název pole pro datum úpravy
        except AttributeError:
            return None

    def location(self, obj):
        # Pokud máš v modelu metodu get_absolute_url, Django ji použije automaticky.
        # Pokud ne, definuj ji přímo zde:
        return reverse('detail_psa', args=[obj.pk])

class StaticViewSitemap(Sitemap):
    """Sitemap pro statické stránky jako Úvod, Ceník, Kontakt."""
    priority = 0.5
    changefreq = 'weekly'

    def items(self):
        return ['home', 'cenik', 'hledat'] # Názvy tvých URL cest

    def location(self, item):
        return reverse(item)