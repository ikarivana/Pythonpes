from datetime import date
from django import forms
from .models import Pes, Prispevek, Plemeno, Ockovani


# Vlastní widget pro počeštění nahrávání souborů
class CzechClearableFileInput(forms.ClearableFileInput):
    clear_checkbox_label = 'Smazat aktuální soubor'
    initial_text = 'Aktuální'
    input_text = 'Změnit'


class PesForm(forms.ModelForm):
    RTG_CHOICES = [
        ('', '--- nevybráno ---'),
        ('A', 'A - Negativní (0/0)'),
        ('B', 'B - Téměř normální (1/1)'),
        ('C', 'C - Lehká dysplazie (2/2)'),
        ('D', 'D - Střední dysplazie (3/3)'),
        ('E', 'E - Těžká dysplazie (4/4)'),
    ]

    rtg_hd = forms.ChoiceField(choices=RTG_CHOICES, required=False, label="DKK (HD) - Kyčle")
    rtg_ed = forms.ChoiceField(choices=RTG_CHOICES, required=False, label="DLK (ED) - Lokty")

    # Pole věk nesmí být povinné ve formuláři (required=False)
    vek = forms.IntegerField(required=False, label="Věk (roky)",
                             widget=forms.NumberInput(attrs={'placeholder': 'Např. 3'}))

    class Meta:
        model = Pes
        fields = [
            'je_ztraceny', 'jmeno', 'vek', 'rasa', 'narozeni', 'fotka', 'cip',
            'cislo_zapisu', 'barva', 'srst', 'popis',
            'rtg_hd', 'rtg_ed', 'rtg_pater', 'genetika_dna', 'bonitace',
            'otec', 'matka', 'otec_manualni', 'matka_manualni',
            'posledni_ockovani', 'posledni_odcerveni',
            'posledni_klistata', 'typ_ochrany_klistata'
        ]
        widgets = {
            'je_ztraceny': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'jmeno': forms.TextInput(attrs={'placeholder': 'Jméno pejska'}),
            'rasa': forms.TextInput(attrs={'placeholder': 'Např. Americký buldok'}),
            'cip': forms.TextInput(attrs={'placeholder': 'Číslo čipu'}),
            'narozeni': forms.DateInput(attrs={'type': 'date'}),
            'fotka': CzechClearableFileInput(attrs={'class': 'form-control'}),
            'posledni_ockovani': forms.DateInput(attrs={'type': 'date'}),
            'posledni_odcerveni': forms.DateInput(attrs={'type': 'date'}),
            'posledni_klistata': forms.DateInput(attrs={'type': 'date'}),
            'typ_ochrany_klistata': forms.Select(attrs={'class': 'form-select'}),
            'popis': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Povaha, zvláštní znamení...'}),
            'genetika_dna': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Výsledky testů...'}),
            'bonitace': forms.TextInput(attrs={'placeholder': 'Např. 5/3a/E1/S'}),
        }
        labels = {
            'je_ztraceny': '🚨 REŽIM "HLEDÁ SE"',
            'jmeno': 'Jméno pejska',
            'vek': 'Věk (roky)',
            'rasa': 'Rasa',
            'fotka': 'Hlavní fotka pejska',
            'cip': 'Číslo čipu',
            'narozeni': 'Datum narození',
            'popis': 'Popis / Poznámky',
            'typ_ochrany_klistata': 'Způsob ochrany (klíšťata)',
            'posledni_klistata': 'Datum poslední aplikace (klíšťata)',
            'posledni_ockovani': 'Datum posledního očkování',
            'posledni_odcerveni': 'Datum posledního odčervení',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        premium_fields = ['rtg_hd', 'rtg_ed', 'rtg_pater', 'genetika_dna', 'bonitace', 'cislo_zapisu', 'otec', 'matka']
        is_premium = False
        if self.request and hasattr(self.request.user, 'profil'):
            is_premium = self.request.user.profil.je_premium

        for name, field in self.fields.items():
            # Základní stylování
            if name == 'je_ztraceny':
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select custom-brown-input'})
            else:
                field.widget.attrs.update({'class': 'form-control custom-brown-input'})

            # Zamykání pro ne-premium
            if name in premium_fields and not is_premium:
                field.disabled = True
                field.required = False
                field.help_text = "🔒 Pouze pro PREMIUM"
                field.widget.attrs.update({'style': 'background-color: #f8f9fa; opacity: 0.7;'})

    def clean(self):
        cleaned_data = super().clean()
        vek = cleaned_data.get('vek')
        narozeni = cleaned_data.get('narozeni')

        # Pokud věk chybí, dopočítáme ho nebo dáme 0 (kvůli IntegrityError)
        if vek is None:
            if narozeni:
                today = date.today()
                cleaned_data['vek'] = today.year - narozeni.year - (
                            (today.month, today.day) < (narozeni.month, narozeni.day))
            else:
                cleaned_data['vek'] = 0
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Pojistka pro instance před uložením do DB
        if instance.vek is None:
            instance.vek = 0
        if commit:
            instance.save()
        return instance


# --- FORMULÁŘ PRO OČKOVÁNÍ ---
class OckovaniForm(forms.ModelForm):
    class Meta:
        model = Ockovani
        fields = ['datum', 'nazev_vakciny', 'poznamka']
        widgets = {
            'datum': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control custom-brown-input'})


# --- FORMULÁŘ PRO SOCIÁLNÍ ZEĎ ---
class PrispevekForm(forms.ModelForm):
    class Meta:
        model = Prispevek
        fields = ['obrazek', 'video', 'text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3}),
            'obrazek': CzechClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control custom-brown-input'})


# --- FORMULÁŘ PRO PLEMENA / AKCE ---
class PlemenoForm(forms.ModelForm):
    class Meta:
        model = Plemeno
        fields = ['nazev', 'popis', 'ikona', 'foto', 'video', 'datum_konani', 'misto', 'poradatel']
        widgets = {
            'datum_konani': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control custom-brown-input'})