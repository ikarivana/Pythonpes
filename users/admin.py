from django.contrib import admin
from . import models

# --- INLINES ---
class GalerieFotkaInline(admin.TabularInline):
    model = models.GalerieFotka  # Opraveno na tvůj název ze serveru
    extra = 1

class GalerieVideoInline(admin.TabularInline):
    model = models.GalerieVideo  # Opraveno na tvůj název ze serveru
    extra = 1

class OckovaniInline(admin.TabularInline):
    model = models.Ockovani
    extra = 1

# --- HLAVNÍ ADMIN PSA ---
@admin.register(models.Pes)
class PesAdmin(admin.ModelAdmin):
    list_display = ('jmeno', 'rasa', 'majitel')
    inlines = [OckovaniInline, GalerieFotkaInline, GalerieVideoInline]
    readonly_fields = ('qr_kod',)

# --- PROFIL MAJITELE ---
@admin.register(models.ProfilMajitele)
class ProfilMajiteleAdmin(admin.ModelAdmin):
    # Tady přidáváme premium_do, aby se dalo v adminu měnit
    list_display = ('uzivatel', 'is_premium', 'premium_do', 'telefon')
    list_editable = ('is_premium', 'premium_do')
    search_fields = ('uzivatel__username',)

# --- OSTATNÍ REGISTRACE ---
@admin.register(models.Prispevek)
class PrispevekAdmin(admin.ModelAdmin):
    list_display = ('autor', 'plemeno', 'datum_pridani')

admin.site.register(models.Plemeno)
admin.site.register(models.Komentar)
admin.site.register(models.Notifikace)
admin.site.register(models.ZdravotniZaznam)
admin.site.register(models.Uspech)