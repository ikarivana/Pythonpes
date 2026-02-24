from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Pes, Ockovani, Prispevek, Plemeno
from django import forms
from .models import Pes

# --- POMOCNÉ TŘÍDY ---

class CzechClearableFileInput(forms.ClearableFileInput):
    """Upravuje popisky u nahrávání souborů do češtiny"""
    clear_checkbox_label = 'Smazat aktuální soubor'
    initial_text = 'Aktuální'
    input_text = 'Změnit'

# --- 1. FORMULÁŘ PRO PSA ---
class PesForm(forms.ModelForm):
    # Definice fotky pro lepší podporu nahrávání z mobilu
    fotka = forms.ImageField(required=False, widget=forms.FileInput(attrs={'accept': 'image/*'}))

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
        # PŘIDÁNA POLE: 'zdravotni_testy' a 'video', aby to sedělo na šablonu
        fields = [
            'jmeno', 'rasa', 'datum_narozeni', 'cip', 'fotka', 'video',
            'posledni_ockovani', 'posledni_odcerveni', 'posledni_klistata', 'typ_ochrany_klistata',
            'rtg_hd', 'rtg_ed', 'rtg_pater', 'zdravotni_testy', 'genetika_dna', 'popis',
            'bonitace', 'otec_manualni', 'matka_manualni'
        ]

        widgets = {
            'datum_narozeni': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'posledni_ockovani': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'posledni_odcerveni': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'posledni_klistata': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'typ_ochrany_klistata': forms.NumberInput(attrs={'inputmode': 'numeric'}),
            'popis': forms.Textarea(attrs={'rows': 3}),
            'zdravotni_testy': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Např. Lokus S, DM...'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control custom-brown-input'})

     # Omezení pro FREE uživatele
        if self.request and not (self.request.user.is_staff or self.request.user.profil.ma_aktivni_premium):
            self.fields['rtg_hd'].help_text = "🔒 Pouze pro ALFA pány"
            self.fields['rtg_ed'].help_text = "🔒 Pouze pro ALFA pány"
            self.fields['genetika_dna'].help_text = "🔒 Pouze pro ALFA pány"


# --- 2. FORMULÁŘE PRO UŽIVATELE ---

class ExtendedRegistrationForm(UserCreationForm):
    """Formulář pro registraci s rozšířenými poli"""
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

class UserUpdateForm(forms.ModelForm):
    """Formulář pro aktualizaci profilu v nastavení"""
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

# --- 3. OSTATNÍ FORMULÁŘE (Sociální síť a zdraví) ---

class PrispevekForm(forms.ModelForm):
    class Meta:
        model = Prispevek
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Napište něco na zeď...'})
        }


class OckovaniForm(forms.ModelForm):
    class Meta:
        model = Ockovani
        # TADY MUSÍ BÝT 'datum_ockovani'
        fields = ['datum_ockovani', 'nazev_vakciny', 'poznamka', 'datum_pristi_navstevy']

        widgets = {
            # TADY TAKÉ 'datum_ockovani'
            'datum_ockovani': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'datum_pristi_navstevy': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'nazev_vakciny': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Např. Nobivac'}),
            'poznamka': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class PlemenoForm(forms.ModelForm):
    class Meta:
        model = Plemeno
        fields = ['nazev']