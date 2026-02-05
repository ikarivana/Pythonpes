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
        fields = ['kategorie', 'titulek', 'text', 'cena', 'mesto', 'telefon', 'obrazek', 'video']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'titulek': forms.TextInput(attrs={'class': 'form-control'}),
            'kategorie': forms.Select(attrs={'class': 'form-select'}),
            'cena': forms.NumberInput(attrs={'class': 'form-control'}),
            'mesto': forms.TextInput(attrs={'class': 'form-control'}),
            'telefon': forms.TextInput(attrs={'class': 'form-control'}),

            # Podpora pro přímé focení/natáčení z mobilu
            'obrazek': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'capture': 'environment'}),
            'video': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/*', 'capture': 'environment'}),
        }