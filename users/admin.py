from django.contrib import admin
from . import models
from .models import Prispevek


# --- INLINES ---
class GalerieFotkaInline(admin.TabularInline):
    model = models.GalerieFotka
    extra = 1


class GalerieVideoInline(admin.TabularInline):
    model = models.GalerieVideo
    extra = 1


class OckovaniInline(admin.TabularInline):
    model = models.Ockovani
    extra = 1


# --- HLAVNÍ ADMIN PSA ---
@admin.register(models.Pes)
class PesAdmin(admin.ModelAdmin):
    list_display = ('jmeno', 'rasa', 'majitel', 'je_ztraceny')
    list_filter = ('je_ztraceny', 'rasa')
    inlines = [OckovaniInline, GalerieFotkaInline, GalerieVideoInline]
    readonly_fields = ('qr_kod',)
    search_fields = ('jmeno', 'cip', 'majitel__uzivatel__username')


# --- PROMO KÓDY ---
@admin.register(models.PromoKod)
class PromoKodAdmin(admin.ModelAdmin):
    list_display = ('kod', 'pocet_dni', 'je_aktivni', 'poznamka')
    list_editable = ('je_aktivni',)
    search_fields = ('kod', 'poznamka')


# --- OSTATNÍ REGISTRACE ---
@admin.register(Prispevek)
class PrispevekAdmin(admin.ModelAdmin):
    list_display = ('autor', 'text', 'datum_pridani')
    list_filter = ('autor', 'datum_pridani')


@admin.register(models.Plemeno)
class PlemenoAdmin(admin.ModelAdmin):
    list_display = ('nazev', 'kategorie', 'slug') # Zobrazí tyto sloupce v seznamu
    prepopulated_fields = {'slug': ('nazev',)} # Automaticky vygeneruje slug z názvu
    list_filter = ('kategorie',) # Umožní filtrovat podle kategorie
    search_fields = ('nazev', 'slug') # Umožní vyhledávat podle názvu nebo slugu

admin.site.register(models.Komentar)
admin.site.register(models.Notifikace)
admin.site.register(models.ZdravotniZaznam)
admin.site.register(models.Uspech)