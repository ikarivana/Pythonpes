from django import forms
from .models import Sluzba
from .models import KontaktniZprava

class SluzbaForm(forms.ModelForm):
    class Meta:
        model = Sluzba
        fields = ['nazev', 'typ', 'adresa', 'popis', 'web', 'telefon', 'lat', 'lon']
        widgets = {
            'nazev': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Název provozovny'}),
            'typ': forms.Select(attrs={'class': 'form-select'}),
            'adresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ulice, město...'}),
            'popis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'web': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'telefon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420...'}),
            'lat': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'lon': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            # Přidá tvou hnědou třídu ke všem polím automaticky
            field.widget.attrs.update({'class': 'form-control custom-brown-input'})

class KontaktForm(forms.ModelForm):
    class Meta:
        model = KontaktniZprava
        fields = ['jmeno', 'email', 'predmet', 'zprava']
        widgets = {
            'jmeno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vaše jméno'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Váš e-mail'}),
            'predmet': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'S čím vám můžeme pomoci?'}),
            'zprava': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Napište vaši zprávu...'}),
        }