from django.contrib import admin
from .models import Inzerat, InzeratFoto


# Umožní přidávat/vidět další fotky přímo u inzerátu
class InzeratFotoInline(admin.TabularInline):
    model = InzeratFoto
    extra = 1


@admin.register(Inzerat)
class InzeratAdmin(admin.ModelAdmin):
    # Tady definuješ sloupce, které uvidíš v tom hlavním seznamu
    # Přidal jsem 'telefon' a 'get_email'
    list_display = ('titulek', 'kategorie', 'get_email', 'telefon', 'kraj', 'aktivni', 'vytvoreno')

    # Umožní filtrovat v pravém panelu
    list_filter = ('kategorie', 'kraj', 'aktivni')

    # Vyhledávání (můžeš hledat i podle telefonu)
    search_fields = ('titulek', 'telefon', 'autor__email', 'mesto')

    # Přidání fotek do detailu
    inlines = [InzeratFotoInline]

    # Speciální funkce pro zobrazení emailu autora v seznamu
    def get_email(self, obj):
        return obj.autor.email

    get_email.short_description = 'Email autora'


# Registrace modelu pro fotky, abys je mohla spravovat i samostatně
admin.site.register(InzeratFoto)
