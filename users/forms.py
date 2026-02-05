from django import forms
from .models import Pes, ProfilMajitele


class PesForm(forms.ModelForm):
    class Meta:
        model = Pes
        # Vybereme pole, která chce majitel vyplňovat
        fields = ['jmeno', 'rasa', 'vek', 'popis', 'fotka', 'cip',]#'posledni_ockovani', 'posledni_odcerveni']

        # Přidáme kalendář pro data (standardně je to jen textové pole)
        widgets = {
            'posledni_ockovani': forms.DateInput(attrs={'type': 'date'}),
            'posledni_odcerveni': forms.DateInput(attrs={'type': 'date'}),
            'popis': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tady můžeme přidat CSS třídy pro náš hnědý design
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control custom-brown-input'})