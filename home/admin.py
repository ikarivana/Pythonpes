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
    list_display = ('nazev', 'typ', 'adresa', 'schvaleno', 'vytvoreno')
    list_filter = ('typ', 'schvaleno', 'vytvoreno')
    search_fields = ('nazev', 'adresa', 'popis')
    list_editable = ('schvaleno',)
    # Pole vytvoreno je auto_now_add, takže musí být readonly, pokud ho chceš vidět v detailu
    readonly_fields = ('vytvoreno',)

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