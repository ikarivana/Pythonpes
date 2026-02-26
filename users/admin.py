from django.contrib import admin
from . import models


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
@admin.register(models.Prispevek)
class PrispevekAdmin(admin.ModelAdmin):
    list_display = ('autor', 'plemeno', 'datum_pridani')
    list_filter = ('plemeno', 'datum_pridani')


admin.site.register(models.Plemeno)
admin.site.register(models.Komentar)
admin.site.register(models.Notifikace)
admin.site.register(models.ZdravotniZaznam)
admin.site.register(models.Uspech)