from django.contrib import admin
from django.utils.html import format_html
from .models import Sluzba, KontaktniZprava, ProfilMajitele # Všechny importy z jednoho místa

@admin.register(Sluzba)
class SluzbaAdmin(admin.ModelAdmin):
    list_display = ('nazev', 'typ', 'adresa', 'schvaleno', 'vytvoreno')
    list_filter = ('typ', 'schvaleno', 'vytvoreno')
    search_fields = ('nazev', 'adresa', 'popis')
    list_editable = ('schvaleno',)

@admin.register(KontaktniZprava)
class KontaktniZpravaAdmin(admin.ModelAdmin):
    list_display = ('jmeno', 'email', 'predmet', 'vytvoreno')
    list_filter = ('vytvoreno',)
    search_fields = ('jmeno', 'email', 'predmet', 'zprava')
    readonly_fields = ('vytvoreno',)

# OPRAVENO: Pouze jeden zavináč
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
        if obj.is_premium:
            return format_html('<b style="color: #c5a059;">👑 ALFA</b>')
        return "Běžný"
    premium_status.short_description = 'Status'