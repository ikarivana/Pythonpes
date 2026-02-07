from django import forms
from .models import Inzerat


# Speciální třída pro podporu více souborů najednou
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class InzeratForm(forms.ModelForm):
    # Pole pro hromadné nahrání fotek do galerie
    galerie_fotky = forms.ImageField(
        widget=MultipleFileInput(attrs={'multiple': True, 'class': 'form-control', 'accept': 'image/*'}),
        required=False,
        label="Další fotografie do galerie"
    )

    class Meta:
        model = Inzerat
        # Přidali jsme 'kraj' do seznamu polí
        fields = ['kategorie', 'titulek', 'text', 'cena', 'kraj', 'mesto', 'telefon', 'obrazek', 'video']

        widgets = {
            'titulek': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Co prodáváte?'}),
            'text': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Popište podrobněji...'}),
            'kategorie': forms.Select(attrs={'class': 'form-select'}),
            'cena': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Kč'}),

            # NOVÉ: Výběr kraje (Select)
            'kraj': forms.Select(attrs={'class': 'form-select'}),

            'mesto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Např. Tábor'}),
            'telefon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420...'}),

            # Podpora pro přímé focení/natáčení z mobilu
            'obrazek': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'capture': 'environment'}),
            'video': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/*', 'capture': 'environment'}),
        }