from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from users.models import Pes


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        # Tyto názvy musí existovat v tvých urls.py
        return ['home', 'kontakt', 'mapa_sluzeb', 'seznam_hledanych', 'seznam_zdi']

    def location(self, item):
        return reverse(item)


class PesSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Pes.objects.all()

    # Django si sám zavolá get_absolute_url z modelu Pes