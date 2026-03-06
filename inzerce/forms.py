from django import forms
from .models import Inzerat


# Speciální widget pro hromadné nahrávání fotek
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class InzeratForm(forms.ModelForm):
    # Pole pro galerii - přidáme mu HeroPets styl
    galerie_fotky = forms.ImageField(
        widget=MultipleFileInput(attrs={
            'multiple': True,
            'class': 'form-control custom-brown-input',
            'accept': 'image/*'
        }),
        required=False,
        label="Přidat další fotky do galerie"
    )

    class Meta:
        model = Inzerat
        fields = ['kategorie', 'titulek', 'text', 'cena', 'kraj', 'mesto', 'telefon', 'obrazek', 'video']

        widgets = {
            'titulek': forms.TextInput(attrs={'placeholder': 'Např. Krásné škrabadlo pro kočky'}),
            'text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Popište stav, velikost nebo důvod prodeje...'}),
            'cena': forms.NumberInput(attrs={'placeholder': 'Kč (nechte prázdné, pokud je zdarma)'}),
            'mesto': forms.TextInput(attrs={'placeholder': 'Např. Brno'}),
            'telefon': forms.TextInput(attrs={'placeholder': '+420 123 456 789'}),

            # Podpora pro mobily s naším stylem
            'obrazek': forms.FileInput(attrs={'accept': 'image/*', 'capture': 'environment'}),
            'video': forms.FileInput(attrs={'accept': 'video/*', 'capture': 'environment'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Sjednocení stylu pro všechna pole (jako u tvých předchozích formulářů)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control custom-brown-input',
                'style': 'border-radius: 15px; border: 1.5px solid var(--border-tan); padding: 12px;'
            })

        # Kategorie a Kraj mají v Bootstrapu třídu form-select, tak ji tam přidáme
        self.fields['kategorie'].widget.attrs['class'] = 'form-select custom-brown-input'
        self.fields['kraj'].widget.attrs['class'] = 'form-select custom-brown-input'

        # Přátelštější labely
        self.fields['obrazek'].label = "Hlavní (náhledová) fotka"
        self.fields['video'].label = "Krátké video (volitelné)"