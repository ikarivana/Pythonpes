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
            'vek': forms.NumberInput(attrs={'placeholder': 'Např. 3'}),
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
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            # Stylování podle typu pole
            if name == 'je_ztraceny':
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select custom-brown-input'})
            else:
                field.widget.attrs.update({'class': 'form-control custom-brown-input'})

# --- FORMULÁŘ PRO OČKOVÁNÍ (HISTORIE) ---

class OckovaniForm(forms.ModelForm):
    class Meta:
        model = Ockovani
        fields = ['datum', 'nazev_vakciny', 'poznamka']
        widgets = {
            'datum': forms.DateInput(attrs={'type': 'date'}),
            'nazev_vakciny': forms.TextInput(attrs={'placeholder': 'Např. Biocan Novel DHPPi'}),
            'poznamka': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'datum': 'Datum očkování',
            'nazev_vakciny': 'Název vakcíny',
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
            'text': forms.Textarea(attrs={'placeholder': 'Napište něco o svém pejskovi...', 'rows': 3}),
            'obrazek': CzechClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'obrazek': 'Obrázek k příspěvku',
            'video': 'Video k příspěvku',
            'text': 'Váš text',
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
            'popis': forms.Textarea(attrs={'rows': 3}),
            'datum_konani': forms.DateInput(attrs={'type': 'date'}),
            'foto': CzechClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'nazev': 'Název plemene nebo akce',
            'datum_konani': 'Datum konání',
            'foto': 'Prezentační foto',
            'video': 'Video',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['foto', 'video', 'ikona']:
                field.widget.attrs.update({'class': 'form-control custom-brown-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})