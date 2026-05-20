from django import forms
# UPRAVENO: Přidán import modelu Clanek
from .models import Sluzba, Recenze, Clanek, Komentar


# =====================================================================
# --- FORMULÁŘ PRO BLOG (NOVÉ) ---
# =====================================================================
class ClanekForm(forms.ModelForm):
    class Meta:
        model = Clanek
        # Použijeme '__all__', což automaticky natáhne VŠECHNA pole z tvého modelu
        fields = '__all__'

        # Z pole slug uděláme skryté nebo nepovinné, protože ho generujeme automaticky ve views
        exclude = ['slug']


        labels = {
            'titulek': 'Název článku',
            'kategorie': 'Kategorie',
            'perex': 'Perex (krátký úvodní text na kartě)',
            'obrazek': 'Úvodní obrázek článku',
            'publikovan': 'Publikovat hned',
        }
        widgets = {
            'perex': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Krátký popis...'}),
            'obrazek': forms.ClearableFileInput(),
            'publikovan': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'text': forms.Textarea(attrs={'required': False}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'publikovan':
                if name == 'kategorie':
                    css_class = 'form-select custom-brown-input'
                else:
                    css_class = 'form-control custom-brown-input'

                field.widget.attrs.update({
                    'class': css_class,
                    'style': 'border-radius: 12px; border: 1.5px solid var(--border-tan); padding: 10px;'

                })

class KomentarForm(forms.ModelForm):
    class Meta:
        model = Komentar
        fields = ['text'] # Případně přidejte 'parent', pokud chcete v budoucnu vybírat rodiče přímo
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Napište svůj komentář...',
                'style': 'border-radius: 12px; border: 1.5px solid var(--border-tan);'
            }),
        }
        labels = {
            'text': '',
        }

# =====================================================================
# --- TVÉ STÁVAJÍCÍ FORMULÁŘE ---
# =====================================================================
class SluzbaForm(forms.ModelForm):
    typ = forms.ChoiceField(
        choices=Sluzba.TYPY_SLUZEB,
        label="Co je to za místo?",
        required=False
    )

    class Meta:
        model = Sluzba
        fields = ['nazev', 'typ', 'adresa', 'popis', 'web', 'telefon', 'lat', 'lon']
        labels = {
            'nazev': 'Název podniku nebo místa',
            'adresa': 'Přesná adresa (ulice, město)',
            'popis': 'Krátký popis pro ostatní páníčky',
            'web': 'Webové stránky (nepovinné)',
            'telefon': 'Kontaktní telefon',
            'lat': 'Zeměpisná šířka (vyplní se z mapy)',
            'lon': 'Zeměpisná délka (vyplní se z mapy)',
        }
        widgets = {
            'popis': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Např. Skvělá káva a miska s vodou vždy připravena...'}),
            'lat': forms.TextInput(attrs={'readonly': 'readonly'}),
            'lon': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['nazev'].required = False
        self.fields['adresa'].required = False
        self.fields['lat'].required = False
        self.fields['lon'].required = False

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control custom-brown-input',
                'style': 'border-radius: 12px; border: 1.5px solid var(--border-tan); padding: 10px;'
            })


class RecenzeForm(forms.ModelForm):
    class Meta:
        model = Recenze
        fields = ['hvezdy', 'text', 'media_soubor']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Jaké to tam bylo? Co by ostatní měli vědět?',
                'rows': 3
            }),
            'hvezdy': forms.HiddenInput(),
        }


class KontaktForm(forms.Form):
    jmeno = forms.CharField(
        label="Vaše jméno",
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Např. Jana a Alík',
            'class': 'form-control custom-brown-input'
        })
    )
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={
            'placeholder': 'vas@email.cz',
            'class': 'form-control custom-brown-input'
        })
    )
    predmet = forms.CharField(
        label="Předmět",
        max_length=200,
        widget=forms.TextInput(attrs={
            'placeholder': 'S čím vám můžeme pomoci?',
            'class': 'form-control custom-brown-input'
        })
    )
    zprava = forms.CharField(
        label="Vaše zpráva",
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'Napište nám, co máte na srdci...',
            'class': 'form-control custom-brown-input'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control custom-brown-input',
                'style': 'border-radius: 12px; border: 1.5px solid var(--border-tan);'
            })