from django import forms
from .models import Pes, Prispevek, Plemeno, Ockovani

class PesForm(forms.ModelForm):
    class Meta:
        model = Pes
        fields = [
            'jmeno', 'rasa', 'vek', 'popis', 'fotka',
            'cip', 'posledni_ockovani', 'posledni_odcerveni', 'posledni_klistata', 'je_ztraceny'
        ]
        widgets = {
            'popis': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Např. povaha, alergie...'}),
            'posledni_ockovani': forms.DateInput(attrs={'type': 'date'}),
            'posledni_odcerveni': forms.DateInput(attrs={'type': 'date'}),
            'posledni_klistata': forms.DateInput(attrs={'type': 'date'}),
            'fotka': forms.FileInput(attrs={'class': 'form-control'}),
            'je_ztraceny': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'je_ztraceny':
                field.widget.attrs.update({'class': 'form-control custom-brown-input'})
            else:
                # Checkboxu necháme jeho specifickou třídu
                field.widget.attrs.update({'class': 'form-check-input'})

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
        fields = ['obrazek', 'video', 'text']
        widgets = {
            'text': forms.Textarea(attrs={
                'placeholder': 'Napište něco o svém pejskovi...',
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control custom-brown-input'})

class PlemenoForm(forms.ModelForm):
    class Meta:
        model = Plemeno
        fields = ['nazev', 'popis', 'ikona', 'datum_konani', 'misto', 'poradatel']
        widgets = {
            'popis': forms.Textarea(attrs={'rows': 3}),
            'datum_konani': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control custom-brown-input'})