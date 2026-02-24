from django import forms
from .models import Sluzba


class SluzbaForm(forms.ModelForm):
    # Přidáme explicitně pole typ s ikonkami přímo pro uživatele
    typ = forms.ChoiceField(
        choices=Sluzba.TYPY_SLUZEB,
        widget=forms.Select(attrs={'class': 'form-control custom-brown-input'})
    )

    class Meta:
        model = Sluzba
        fields = ['nazev', 'typ', 'adresa', 'popis', 'web', 'telefon', 'lat', 'lon']
        widgets = {
            'lat': forms.TextInput(attrs={'placeholder': 'Např. 49.397'}),
            'lon': forms.TextInput(attrs={'placeholder': 'Např. 17.678'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'typ':
                field.widget.attrs.update({'class': 'form-control custom-brown-input'})


class KontaktForm(forms.Form):
    jmeno = forms.CharField(label="Vaše jméno", max_length=100,
                            widget=forms.TextInput(
                                attrs={'class': 'form-control custom-brown-input', 'placeholder': 'Alík Novák'}))
    email = forms.EmailField(label="E-mail",
                             widget=forms.EmailInput(
                                 attrs={'class': 'form-control custom-brown-input', 'placeholder': 'vas@email.cz'}))
    predmet = forms.CharField(label="Předmět", max_length=200,
                              widget=forms.TextInput(
                                  attrs={'class': 'form-control custom-brown-input', 'placeholder': 'Předmět zprávy'}))
    zprava = forms.CharField(label="Zpráva",
                             widget=forms.Textarea(attrs={'class': 'form-control custom-brown-input', 'rows': 4,
                                                          'placeholder': 'Co máte na srdci?'}))