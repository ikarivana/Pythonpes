from django.contrib import admin
from .models import (
    ProfilMajitele, Pes, Ockovani, Galerie,
    Video, Uspech, ZdravotniZaznam, Plemeno,
    Prispevek, Komentar, Notifikace
)

# --- INLINES ---
class OckovaniInline(admin.TabularInline):
    model = Ockovani
    extra = 1

class GalerieInline(admin.TabularInline):
    model = Galerie
    extra = 1

class UspechInline(admin.TabularInline):
    model = Uspech
    extra = 1

# --- REGISTRACE HLAVNÍCH MODELŮ ---

@admin.register(ProfilMajitele)
class ProfilMajiteleAdmin(admin.ModelAdmin):
    list_display = ('uzivatel', 'telefon', 'is_premium')
    search_fields = ('uzivatel__username',)

@admin.register(Pes)
class PesAdmin(admin.ModelAdmin):
    list_display = ('jmeno', 'rasa', 'majitel', 'je_ztraceny')
    inlines = [OckovaniInline, GalerieInline, UspechInline]
    readonly_fields = ('qr_kod',)

@admin.register(Plemeno)
class PlemenoAdmin(admin.ModelAdmin):
    list_display = ('nazev', 'slug')
    # Tohle zajistí, že když píšeš Název, Slug se dopisuje sám
    prepopulated_fields = {'slug': ('nazev',)}

@admin.register(Prispevek)
class PrispevekAdmin(admin.ModelAdmin):
    list_display = ('autor', 'plemeno', 'datum_pridani')
    list_filter = ('plemeno',)

# --- OSTATNÍ REGISTRACE (Aby tam bylo vše) ---
admin.site.register(Notifikace)
admin.site.register(Komentar)
admin.site.register(ZdravotniZaznam)
admin.site.register(Video)