from django.contrib import admin
from django.utils.html import format_html
from . import models


# --- INLINES ---
class GalerieFotkaInline(admin.TabularInline):
    model = models.GalerieFotka
    extra = 1
    readonly_fields = ('nahled',)

    def nahled(self, obj):
        # OPRAVA: V modelu GalerieFotka máš pole 'obrazek', ne 'soubor'
        if obj.obrazek:
            return format_html('<img src="{}" style="width: 50px; height: auto; border-radius: 5px;" />',
                               obj.obrazek.url)
        return "-"


class GalerieVideoInline(admin.TabularInline):
    # OPRAVA: V modelu GalerieVideo máš pole 'video_soubor'
    model = models.GalerieVideo
    extra = 1


class OckovaniInline(admin.TabularInline):
    model = models.Ockovani
    extra = 1


# --- ADMIN PSA (HLAVNÍ) ---
@admin.register(models.Pes)
class PesAdmin(admin.ModelAdmin):
    # OPRAVA: Odstraněno 'pohlavi', které v modelu Pes nemáš
    list_display = ('nahled_foto', 'jmeno', 'druh_ikona', 'rasa', 'majitel', 'je_ztraceny')
    list_filter = ('je_ztraceny', 'druh', 'rasa')
    list_editable = ('je_ztraceny',)
    search_fields = ('jmeno', 'cip', 'majitel__uzivatel__username', 'majitel__uzivatel__email')
    readonly_fields = ('qr_kod', 'nahled_velky')
    inlines = [OckovaniInline, GalerieFotkaInline, GalerieVideoInline]

    fieldsets = (
        ('Základní informace', {
            # OPRAVA: Odstraněno 'pohlavi' (v modelu ho nemáš)
            'fields': (('jmeno', 'druh'), ('rasa', 'majitel'), 'cip')
        }),
        ('Zdraví a Status', {
            'fields': ('je_ztraceny', 'qr_kod', 'nahled_velky'),
        }),
    )

    def nahled_foto(self, obj):
        # OPRAVA: Vztah ForeignKey má related_name 'galerie_fotky'
        prvni_foto = obj.galerie_fotky.first()
        if prvni_foto and prvni_foto.obrazek:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;" />',
                prvni_foto.obrazek.url)
        return format_html('<span style="color: #ccc;">🐾</span>')

    nahled_foto.short_description = "Foto"

    def nahled_velky(self, obj):
        prvni_foto = obj.galerie_fotky.first()
        if prvni_foto and prvni_foto.obrazek:
            return format_html('<img src="{}" style="max-width: 200px; border-radius: 10px;" />', prvni_foto.obrazek.url)
        return "Není nahrána žádná fotka."

    def druh_ikona(self, obj):
        ikony = {'pes': '🐕', 'kocka': '🐈'}
        return ikony.get(obj.druh, '🐾')

    druh_ikona.short_description = "Druh"


# --- SOCIÁLNÍ SÍŤ ---
@admin.register(models.Prispevek)
class PrispevekAdmin(admin.ModelAdmin):
    list_display = ('autor', 'nahled_media', 'zkraceny_text', 'datum_pridani', 'plemeno')
    list_filter = ('datum_pridani', 'plemeno')
    search_fields = ('text', 'autor__username')

    def zkraceny_text(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text

    def nahled_media(self, obj):
        if obj.obrazek:
            return format_html('<img src="{}" style="width: 50px; border-radius: 5px;" />', obj.obrazek.url)
        elif obj.video:
            return "🎥 Video"
        return "Text"


# --- PLEMENA A ZDI ---
@admin.register(models.Plemeno)
class PlemenoAdmin(admin.ModelAdmin):
    list_display = ('nazev', 'kategorie', 'slug', 'pocet_prispevku')
    prepopulated_fields = {'slug': ('nazev',)}
    list_filter = ('kategorie',)
    search_fields = ('nazev', 'slug')

    def pocet_prispevku(self, obj):
        # OPRAVA: Related name je 'prispevky_na_zed'
        return obj.prispevky_na_zed.count()


# --- SYSTÉMOVÉ ---
@admin.register(models.Notifikace)
class NotifikaceAdmin(admin.ModelAdmin):
    # OPRAVA: Pole 'datum' v modelu nemáš, jmenuje se 'datum_vytvoreni'
    list_display = ('prijemce', 'typ', 'precteno', 'datum_vytvoreni')
    list_filter = ('precteno', 'typ')
    search_fields = ('prijemce__username',)


@admin.register(models.ZdravotniZaznam)
class ZdravotniZaznamAdmin(admin.ModelAdmin):
    # OPRAVA: Pole 'typ' v modelu ZdravotniZaznam NEMÁŠ. Odstraněno z list_display a list_filter.
    list_display = ('pes', 'titulek', 'datum_vytvoreni')
    list_filter = ('datum_vytvoreni',)
    search_fields = ('titulek', 'popis', 'pes__jmeno')


@admin.register(models.PromoKod)
class PromoKodAdmin(admin.ModelAdmin):
    list_display = ('kod', 'pocet_dni', 'je_aktivni', 'poznamka')
    list_editable = ('je_aktivni',)
    search_fields = ('kod',)


# Ostatní jednoduché registrace
admin.site.register(models.Komentar)
admin.site.register(models.Uspech)

# Vlastní titulek administrace
admin.site.site_header = "🐾 HeroPets: Administrace smečky"
admin.site.site_title = "HeroPets Admin"
admin.site.index_title = "Správa hrdinů a komunity"