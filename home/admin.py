from django.contrib import admin
from .models import Sluzba

@admin.register(Sluzba)
class SluzbaAdmin(admin.ModelAdmin):
    list_display = ('nazev', 'typ', 'schvaleno', 'vytvoreno') # Uvidíš tabulku s fajfkama
    list_filter = ('schvaleno', 'typ') # Můžeš si vyfiltrovat jen ty neschválené
    list_editable = ('schvaleno',) # Můžeš to "odfajfkovat" přímo v seznamu bez rozkliknutí
