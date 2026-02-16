from django.contrib import admin
from .models import (
    ProfilMajitele, Pes, Ockovani, Galerie,
    Video, Uspech, ZdravotniZaznam, Plemeno,
    Prispevek, Komentar, Notifikace
)


# --- INLINES (vnořené editory pro Psa) ---

class OckovaniInline(admin.TabularInline):
    model = Ockovani
    extra = 1


class GalerieInline(admin.TabularInline):
    model = Galerie
    extra = 1


class UspechInline(admin.TabularInline):
    model = Uspech
    extra = 1


# --- REGISTRACE MODELŮ ---

@admin.register(ProfilMajitele)
class ProfilMajiteleAdmin(admin.ModelAdmin):
    list_display = ('uzivatel', 'telefon', 'is_premium', 'premium_do')
    list_filter = ('is_premium',)
    search_fields = ('uzivatel__username', 'telefon')


@admin.register(Pes)
class PesAdmin(admin.ModelAdmin):
    # V seznamu psů uvidíme nejdůležitější info
    list_display = ('jmeno', 'rasa', 'majitel', 'cip', 'je_ztraceny', 'vytvoreno')
    list_filter = ('rasa', 'je_ztraceny')
    search_fields = ('jmeno', 'cip', 'majitel__uzivatel__username')

    # Přidáme vnořené úpravy přímo k psovi
    inlines = [OckovaniInline, GalerieInline, UspechInline]

    # QR kód nechceme v adminu měnit ručně, generuje se sám
    readonly_fields = ('qr_kod',)


@admin.register(Plemeno)
class PlemenoAdmin(admin.ModelAdmin):
    list_display = ('nazev', 'slug')
    prepopulated_fields = {'slug': ('nazev',)}


@admin.register(Prispevek)
class PrispevekAdmin(admin.ModelAdmin):
    list_display = ('autor', 'plemeno', 'datum_pridani')
    list_filter = ('plemeno', 'datum_pridani')
    search_fields = ('text', 'autor__username')


# Ostatní modely zaregistrujeme jednoduše
admin.site.register(Notifikace)
admin.site.register(Komentar)
admin.site.register(ZdravotniZaznam)
admin.site.register(Video)
