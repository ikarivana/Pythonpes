from django import forms
from .models import Sluzba


class SluzbaForm(forms.ModelForm):
    # Přidáme explicitně pole typ s ikonkami
    typ = forms.ChoiceField(
        choices=Sluzba.TYPY_SLUZEB,
        label="Co je to za místo?",
        required=False  # Uděláme i typ nepovinný, pokud by zlobil
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

        # KLÍČOVÁ ZMĚNA: Nastavíme pole jako nepovinná
        self.fields['nazev'].required = False
        self.fields['adresa'].required = False
        self.fields['lat'].required = False
        self.fields['lon'].required = False

        # Hromadné přidání třídy pro stylování
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control custom-brown-input',
                'style': 'border-radius: 12px; border: 1.5px solid var(--border-tan); padding: 10px;'
            })


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
        # Sjednocení stylu i pro kontaktní formulář
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control custom-brown-input',
                'style': 'border-radius: 12px; border: 1.5px solid var(--border-tan);'
            })