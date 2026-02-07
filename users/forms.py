from django import forms
from .models import Pes, Prispevek, Plemeno, Ockovani


class PesForm(forms.ModelForm):
    class Meta:
        model = Pes
        fields = [
            'jmeno', 'rasa', 'vek', 'popis', 'fotka',
            'cip', 'posledni_ockovani', 'posledni_odcerveni'
        ]
        # Tady necháme jen to, co NENÍ třída (aby to bylo přehledné)
        widgets = {
            'popis': forms.Textarea(attrs={'rows': 3}),
            'posledni_ockovani': forms.DateInput(attrs={'type': 'date'}),
            'posledni_odcerveni': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tento cyklus projde VŠECHNA pole a přidá jim tvoji hnědou třídu
        for field in self.fields.values():
            # Použijeme update, abychom nesmazali type="date" u kalendářů
            field.widget.attrs.update({'class': 'form-control custom-brown-input'})

class OckovaniForm(forms.ModelForm):
    class Meta:
        model = Ockovani
        fields = ['datum', 'nazev_vakciny', 'poznamka']
        widgets = {
            'datum': forms.DateInput(attrs={'type': 'date'}),
            'nazev_vakciny': forms.TextInput(attrs={'placeholder': 'Např. Vzteklina (Rabisin)'}),
            'poznamka': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Doplňující info...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control custom-brown-input'})




class PrispevekForm(forms.ModelForm):
    class Meta:
        model = Prispevek
        fields = ['obrazek', 'video', 'text']  # Plemeno nastavíme automaticky ve view
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control custom-brown-input',
                'placeholder': 'Napište něco o svém pejskovi...',
                'rows': 3
            }),
            'obrazek': forms.FileInput(attrs={'class': 'form-control mb-2'}),
            'video': forms.FileInput(attrs={'class': 'form-control mb-2'}),
        }

class PlemenoForm(forms.ModelForm):
    class Meta:
        model = Plemeno
        fields = ['nazev', 'popis', 'ikona', 'datum_konani', 'misto', 'poradatel']
        widgets = {
            'nazev': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zadejte název...'}),
            'popis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Krátký popis...'}),
            'datum_konani': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'misto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kde se akce koná?'}),
            'poradatel': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kdo akci pořádá?'}),
        }