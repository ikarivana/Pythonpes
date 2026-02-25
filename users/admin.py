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


# --- PROFIL MAJITELE ---
@admin.register(models.ProfilMajitele)
class ProfilMajiteleAdmin(admin.ModelAdmin):
    # Přidali jsme adresu a použitý promo kód do přehledu
    list_display = ('uzivatel', 'is_premium', 'premium_do', 'pouzity_kod', 'mesto', 'telefon')
    # Umožníme měnit premium status a adresu přímo v tabulce pro rychlou opravu
    list_editable = ('is_premium', 'premium_do')
    # Filtrování, abys rychle našla lidi z konkrétního útulku nebo výstavy
    list_filter = ('is_premium', 'pouzity_kod', 'mesto')
    search_fields = ('uzivatel__username', 'uzivatel__email', 'pouzity_kod', 'mesto')

    # Organizace polí v detailu profilu
    fieldsets = (
        ('Základní údaje', {
            'fields': ('uzivatel', 'telefon')
        }),
        ('Doručovací adresa pro dárky', {
            'fields': ('ulice_cp', 'mesto', 'psc')
        }),
        ('Premium a Marketing', {
            'fields': ('is_premium', 'premium_do', 'pouzity_kod'),
            'description': 'Zde vidíte, zda uživatel získal premium přes promo kód.'
        }),
    )


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