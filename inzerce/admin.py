from django.contrib import admin
from django.utils.html import format_html
from .models import Inzerat, InzeratFoto


class InzeratFotoInline(admin.TabularInline):
    model = InzeratFoto
    extra = 1
    readonly_fields = ('nahled_fotky',)

    def nahled_fotky(self, obj):
        if obj.foto:
            return format_html('<img src="{}" style="width: 100px; height: auto; border-radius: 5px;" />', obj.foto.url)
        return "Žádná fotka"

    nahled_fotky.short_description = 'Náhled'


@admin.register(Inzerat)
class InzeratAdmin(admin.ModelAdmin):
    # Zobrazení klíčových informací včetně náhledu a statusu Premium
    list_display = ('nahled_hlavni_fotky', 'titulek', 'kategorie', 'je_premium_uzivatel', 'kraj', 'aktivni',
                    'vytvoreno')

    # Filtrování podle důležitých metrik
    list_filter = ('aktivni', 'kategorie', 'kraj', 'vytvoreno')

    # Rozšířené vyhledávání
    search_fields = ('titulek', 'text', 'autor__username', 'autor__email', 'mesto', 'telefon')

    # Možnost rychle změnit aktivitu inzerátu přímo v seznamu
    list_editable = ('aktivni',)

    inlines = [InzeratFotoInline]

    # Funkce pro náhled hlavní fotky v seznamu
    def nahled_hlavni_fotky(self, obj):
        if obj.obrazek:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 50%; border: 1px solid #c5a059;" />',
                obj.obrazek.url)
        return "—"

    nahled_hlavni_fotky.short_description = 'Foto'

    # Funkce pro zobrazení Premium statusu autora
    def je_premium_uzivatel(self, obj):
        status = getattr(obj.autor.profil, 'is_premium', False)
        if status:
            return format_html('<span style="color: #c5a059; font-weight: bold;">👑 ALFA</span>')
        return "Běžný"

    je_premium_uzivatel.short_description = 'Status'


# Samostatná registrace fotek (pokud bys je chtěla hromadně mazat/spravovat)
@admin.register(InzeratFoto)
class InzeratFotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'inzerat', 'nahled_foto')

    def nahled_foto(self, obj):
        if obj.foto:
            return format_html('<img src="{}" style="width: 80px; border-radius: 5px;" />', obj.foto.url)
        return "—"
