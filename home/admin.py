from django.contrib import admin
from .models import Sluzba, KontaktniZprava


@admin.register(Sluzba)
class SluzbaAdmin(admin.ModelAdmin):
    # Přehledná tabulka služeb
    list_display = ('nazev', 'typ', 'adresa', 'schvaleno', 'vytvoreno')

    # Filtrování v pravém panelu
    list_filter = ('typ', 'schvaleno', 'vytvoreno')

    # Vyhledávání podle názvu a adresy
    search_fields = ('nazev', 'adresa', 'popis')

    # Možnost rychle schválit službu přímo ze seznamu
    list_editable = ('schvaleno',)


@admin.register(KontaktniZprava)
class KontaktniZpravaAdmin(admin.ModelAdmin):
    list_display = ('jmeno', 'email', 'predmet', 'vytvoreno')
    list_filter = ('vytvoreno',)
    search_fields = ('jmeno', 'email', 'predmet', 'zprava')
    # Zprávy v adminu většinou nechceme editovat, jen číst
    readonly_fields = ('vytvoreno',)