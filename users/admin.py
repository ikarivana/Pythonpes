from django.contrib import admin
from django.utils.html import format_html
from . import models


# --- INLINES (Všechny související věci v jednom detailu psa) ---

class OckovaniInline(admin.TabularInline):
    model = models.Ockovani
    extra = 1


class GalerieFotkaInline(admin.TabularInline):
    model = models.GalerieFotka
    extra = 1
    readonly_fields = ('nahled',)

    def nahled(self, obj):
        if obj.obrazek:
            return format_html('<img src="{}" style="height: 50px;"/>', obj.obrazek.url)
        return "-"


class GalerieVideoInline(admin.TabularInline):
    model = models.GalerieVideo
    extra = 1


class VystavaInline(admin.TabularInline):
    model = models.Vystava
    extra = 1


class VrhInline(admin.TabularInline):
    model = models.Vrh
    fk_name = 'rodic'  # Musíme specifikovat, protože model Vrh používá název 'rodic'
    extra = 1


class UspechInline(admin.TabularInline):
    model = models.Uspech
    extra = 1


class ZdravotniZaznamInline(admin.TabularInline):
    model = models.ZdravotniZaznam
    extra = 1


# --- ADMIN PSA ---
@admin.register(models.Pes)
class PesAdmin(admin.ModelAdmin):
    list_display = ('nahled_foto', 'jmeno', 'druh_ikona', 'rasa', 'majitel', 'je_ztraceny')
    list_filter = ('druh', 'je_ztraceny', 'rasa')
    search_fields = ('jmeno', 'cip', 'majitel__uzivatel__username')
    readonly_fields = ('qr_kod', 'nahled_velky', 'vytvoreno')

    # Registrace všech Inlines najednou
    inlines = [
        OckovaniInline,
        ZdravotniZaznamInline,
        UspechInline,
        VystavaInline,
        VrhInline,
        GalerieFotkaInline,
        GalerieVideoInline
    ]

    fieldsets = (
        ('Základní informace', {
            'fields': (('jmeno', 'druh'), ('rasa', 'majitel'), ('datum_narozeni', 'vaha'), 'cip', 'fotka')
        }),
        ('Zdraví, RTG a Dokumentace', {
            'fields': (('rtg_hd', 'rtg_ed', 'rtg_pater'), 'bonitace', 'rodokmen_pdf'),
        }),
        ('Rodokmen (Rodiče)', {
            'fields': (('otec_manualni', 'matka_manualni'), 'chovna_stanice'),
            'classes': ('collapse',),
        }),
        ('SOS & Lokalizace', {
            'fields': ('je_ztraceny', 'je_u_nalezece', ('lat', 'lon'), 'qr_kod', 'nahled_velky'),
        }),
        ('SOS Kontakty', {
            'fields': ('kontaktni_jmeno', 'kontaktni_telefon', 'kontaktni_email', 'adresa_pro_darky'),
            'classes': ('collapse',),
        }),
        ('Prevence a Texty', {
            'fields': (('hlavni_veterinar_nazev', 'hlavni_veterinar_telefon'),
                       ('posledni_ockovani', 'posledni_odcerveni', 'posledni_klistata'),
                       'zdravotni_poznamky', 'popis'),
        }),
    )

    def nahled_foto(self, obj):
        if obj.fotka:
            return format_html(
                '<img src="{}" style="width: 35px; height: 35px; border-radius: 50%; object-fit: cover;" />',
                obj.fotka.url)
        return "🐾"

    def nahled_velky(self, obj):
        if obj.fotka:
            return format_html('<img src="{}" style="max-width: 200px; border-radius: 10px;" />', obj.fotka.url)
        return "Bez fotky"

    def druh_ikona(self, obj):
        return "🐕" if obj.druh == 'pes' else "🐈"


# --- SOCIÁLNÍ SÍŤ A OSTATNÍ ---

@admin.register(models.Prispevek)
class PrispevekAdmin(admin.ModelAdmin):
    list_display = ('autor', 'plemeno', 'datum_pridani', 'pocet_lajku')
    list_filter = ('datum_pridani', 'plemeno')

    def pocet_lajku(self, obj):
        return obj.likes.count()


@admin.register(models.Plemeno)
class PlemenoAdmin(admin.ModelAdmin):
    list_display = ('nazev', 'kategorie', 'slug')
    prepopulated_fields = {'slug': ('nazev',)}


@admin.register(models.Notifikace)
class NotifikaceAdmin(admin.ModelAdmin):
    list_display = ('prijemce', 'odesilatel', 'typ', 'precteno', 'datum_vytvoreni')
    list_filter = ('precteno', 'typ')

#@admin.register(models.ProfilMajitele)
#class ProfilMajiteleAdmin(admin.ModelAdmin):
   # list_display = ('uzivatel', 'is_premium', 'premium_do', 'mesto')
    #list_editable = ('is_premium',)

@admin.register(models.PromoKod)
class PromoKodAdmin(admin.ModelAdmin):
    list_display = ('kod', 'pocet_dni', 'je_aktivni', 'poznamka')

# Pouze ty modely, které nemají nahoře definovanou vlastní třídu (Class)
admin.site.register(models.Komentar)
admin.site.register(models.Like)

