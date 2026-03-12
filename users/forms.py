from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Pes, Ockovani, Prispevek, Plemeno, ProfilMajitele, PromoKod, Vystava, Vrh


# --- POMOCNÉ TŘÍDY ---

class CzechClearableFileInput(forms.ClearableFileInput):
    """Upravuje popisky u nahrávání souborů do češtiny"""
    clear_checkbox_label = 'Smazat aktuální soubor'
    initial_text = 'Aktuální'
    input_text = 'Změnit'


# --- 1. FORMULÁŘ PRO PSA (OPRAVENÁ VERZE) ---
class PesForm(forms.ModelForm):
    # Definice RTG výběru pro pole
    RTG_CHOICES = [
        ('', '--- nevybráno ---'),
        ('A', 'A - Negativní (0/0)'),
        ('B', 'B - Téměř normální (1/1)'),
        ('C', 'C - Lehká dysplazie (2/2)'),
        ('D', 'D - Střední dysplazie (3/3)'),
        ('E', 'E - Těžká dysplazie (4/4)'),
    ]

    class Meta:
        model = Pes
        # Vyloučíme pole, která spravujeme ručně ve views
        exclude = ['majitel', 'qr_kod', 'vytvoreno', 'foto_pozice', 'foto_rotace', 'adresa_pro_darky',
                   'poznamky_ockovani']

        widgets = {
            'jmeno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Jméno parťáka'}),
            'rasa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Např. Border kolie'}),
            # V modelu máš rasa, ne plemeno
            'datum_narozeni': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cip': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Číslo mikročipu'}),
            'vaha': forms.NumberInput(attrs={'step': '0.1', 'class': 'form-control'}),

            # Zdravotní sekce
            'posledni_ockovani': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'posledni_odcerveni': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'posledni_klistata': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),

            # SOS sekce
            'kontaktni_telefon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420...'}),
            'popis': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Vzkaz pro nálezce...'}),

            # Chovné (Premium)
            'bonitace': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'vystavy': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(PesForm, self).__init__(*args, **kwargs)

        # Nastavení RTG výběrů (pokud existují v modelu)
        for rtg_field in ['rtg_hd', 'rtg_ed']:
            if rtg_field in self.fields:
                self.fields[rtg_field] = forms.ChoiceField(
                    choices=self.RTG_CHOICES,
                    required=False,
                    widget=forms.Select(attrs={'class': 'form-control'})
                )

        # Dynamické popisky a Premium logika
        for field_name, field in self.fields.items():
            # Premium pole k zamknutí
            premium_fields = ['rtg_hd', 'rtg_ed', 'rtg_pater', 'bonitace', 'vystavy', 'chovna_stanice']

            if field_name in premium_fields:
                if self.request and not (self.request.user.is_staff or self.request.user.profil.is_premium):
                    field.disabled = True
                    field.help_text = "🔒 Funkce pro Premium členy"

            # Úprava popisků podle druhu (Pes vs Kočka)
            if self.instance and self.instance.druh == 'kocka':
                if field_name == 'jmeno': field.label = "Jméno kočky"
                if field_name == 'bonitace': field.label = "Uchovnění kočky"
            else:
                if field_name == 'jmeno': field.label = "Jméno psa"

        # Povinná pole
        if 'jmeno' in self.fields: self.fields['jmeno'].required = True
        if 'kontaktni_telefon' in self.fields: self.fields['kontaktni_telefon'].required = True


# --- 2. FORMULÁŘE PRO UŽIVATELE ---

class ExtendedRegistrationForm(UserCreationForm):
    first_name = forms.CharField(required=True, label="Jméno")
    last_name = forms.CharField(required=True, label="Příjmení")
    email = forms.EmailField(required=True, label="E-mail")
    telefon = forms.CharField(required=True, label="Telefon")
    ulice_cp = forms.CharField(required=False, label="Ulice a č.p.")
    mesto = forms.CharField(required=False, label="Město")
    psc = forms.CharField(required=False, label="PSČ")
    promo_kod = forms.CharField(required=False, label="Promo kód",
                                widget=forms.TextInput(attrs={'placeholder': 'Máš kód?'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.email = self.cleaned_data.get('email')
        if commit:
            user.save()
            # ... zbytek tvého save kódu pro ProfilMajitele, který jsi tam měl ...
            ProfilMajitele.objects.update_or_create(
                uzivatel=user,
                defaults={
                    'telefon': self.cleaned_data.get('telefon'),
                    'ulice_cp': self.cleaned_data.get('ulice_cp'),
                    'mesto': self.cleaned_data.get('mesto'),
                    'psc': self.cleaned_data.get('psc'),
                }
            )
        return user

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

class ProfilUpdateForm(forms.ModelForm):
    class Meta:
        model = ProfilMajitele
        fields = ['telefon', 'ulice_cp', 'mesto', 'psc']
        widgets = {
            'telefon': forms.TextInput(attrs={'placeholder': 'Telefon'}),
            'ulice_cp': forms.TextInput(attrs={'placeholder': 'Ulice a č.p.'}),
            'mesto': forms.TextInput(attrs={'placeholder': 'Město'}),
            'psc': forms.TextInput(attrs={'placeholder': 'PSČ'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

class PlemenoForm(forms.ModelForm):
    class Meta:
        model = Plemeno
        fields = ['nazev', 'ikona', 'kategorie']


# --- 3. OSTATNÍ FORMULÁŘE ---

class PrispevekForm(forms.ModelForm):
    class Meta:
        model = Prispevek
        fields = ['text', 'obrazek', 'video']
        widgets = {
            'text': forms.Textarea(attrs={'placeholder': 'Co je nového?', 'class': 'form-control'}),
            'obrazek': forms.FileInput(attrs={'id': 'id_obrazek', 'accept': 'image/*'}),
            'video': forms.FileInput(attrs={'id': 'id_video', 'accept': 'video/*'}),
        }


class OckovaniForm(forms.ModelForm):
    class Meta:
        model = Ockovani
        fields = ['datum_ockovani', 'nazev_vakciny', 'poznamka', 'datum_pristi_navstevy']
        widgets = {
            'datum_ockovani': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'datum_pristi_navstevy': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'nazev_vakciny': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Např. Nobivac'}),
            'poznamka': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class VystavaForm(forms.ModelForm):
    class Meta:
        model = Vystava
        fields = ['datum', 'nazev', 'misto', 'oceneni', 'rozhodci']
        widgets = {
            'datum': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'nazev': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Název výstavy'}),
            'oceneni': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'V1, CAC, CACIB...'}),
        }

class VrhForm(forms.ModelForm):
    class Meta:
        model = Vrh
        fields = ['datum_narozeni', 'oznaceni_vrhu', 'pocet_psu', 'pocet_fen', 'druhy_rodic', 'poznamka']
        widgets = {
            'datum_narozeni': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'oznaceni_vrhu': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Např. Vrh A'}),
            'poznamka': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
