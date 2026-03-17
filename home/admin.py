from django.contrib import admin  # HLAVNÍ IMPORT (Django admin)
from django.utils.html import format_html
from django.utils import timezone

# Importy tvých modelů z home/models.py
from .models import Sluzba, KontaktniZprava

# Import modelu z jiné aplikace (users)
from users.models import ProfilMajitele

# --- ADMINISTRACE SLUŽEB ---
@admin.register(Sluzba)
class SluzbaAdmin(admin.ModelAdmin):
    # Definujeme, co uvidíš v tabulce
    list_display = ('barevny_typ', 'nazev', 'adresa', 'vytvoreno', 'potvrzeni_minus', 'schvaleno_ikona')
    list_filter = ('typ', 'schvaleno', 'vytvoreno')
    search_fields = ('nazev', 'adresa')

    # Funkce pro barevné štítky v seznamu
    def barevny_typ(self, obj):
        colors = {
            'nebezpeci': '#8b0000',  # Tmavě červená
            'ztrata': '#ff0000',  # Jasně červená
        }
        color = colors.get(obj.typ, '#3e2723')  # Ostatní hnědá
        return format_html(
            '<b style="color: {}; text-transform: uppercase;">{}</b>',
            color,
            obj.get_typ_display()
        )

    barevny_typ.short_description = 'Typ hlášení'

    # Funkce pro hezčí zobrazení schválení
    def schvaleno_ikona(self, obj):
        if obj.schvaleno:
            return format_html('<span style="color: green;">✔ Schváleno</span>')
        if obj.typ in ['nebezpeci', 'ztrata']:
            return format_html('<span style="color: orange;">⚡ Živé (SOS)</span>')
        return format_html('<span style="color: gray;">⌛ Čeká</span>')

    schvaleno_ikona.short_description = 'Stav schválení'

# --- ADMINISTRACE KONTAKTNÍCH ZPRÁV ---
@admin.register(KontaktniZprava)
class KontaktniZpravaAdmin(admin.ModelAdmin):
    # Tady přidáme i ten "svítící" stav pro nové zprávy
    list_display = ('status_novinky', 'jmeno', 'email', 'predmet', 'vytvoreno')
    list_filter = ('vytvoreno',)
    search_fields = ('jmeno', 'email', 'predmet', 'zprava')
    readonly_fields = ('vytvoreno',)

    def status_novinky(self, obj):
        dnes = timezone.now().date()
        if obj.vytvoreno.date() == dnes:
            return format_html('<span style="color: #2d6a4f; font-weight: 800;">✨ NOVÁ</span>')
        return format_html('<span style="color: #6c757d;">Archiv</span>')
    status_novinky.short_description = 'Stav'

# --- ADMINISTRACE PROFILU MAJITELE ---
@admin.register(ProfilMajitele)
class ProfilMajiteleAdmin(admin.ModelAdmin):
    list_display = ('uzivatel_link', 'premium_status', 'premium_do', 'mesto', 'telefon')
    list_filter = ('is_premium',)
    search_fields = ('uzivatel__email', 'uzivatel__username', 'telefon')
    list_editable = ('premium_do',)

    def uzivatel_link(self, obj):
        return obj.uzivatel.username
    uzivatel_link.short_description = 'Uživatel'

    def premium_status(self, obj):
        # Tady ti svítí ten zlatý ALFA status
        if obj.is_premium:
            return format_html('<b style="color: #c5a059;">👑 ALFA</b>')
        return "Běžný"
    premium_status.short_description = 'Status'