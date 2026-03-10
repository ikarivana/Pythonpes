from datetime import timedelta, date
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Pes, Ockovani, Prispevek, Plemeno, ProfilMajitele, PromoKod


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
            kod_text = self.cleaned_data.get('promo_kod', '').strip()
            is_premium, premium_do, final_kod = False, None, None
            if kod_text:
                try:
                    pkod = PromoKod.objects.get(kod__iexact=kod_text, je_aktivni=True)
                    is_premium = True
                    premium_do = date.today() + timedelta(days=pkod.pocet_dni)
                    final_kod = pkod.kod.upper()
                except PromoKod.DoesNotExist:
                    final_kod = f"NEPLATNÝ: {kod_text}"

            ProfilMajitele.objects.update_or_create(
                uzivatel=user,
                defaults={
                    'telefon': self.cleaned_data.get('telefon'),
                    'ulice_cp': self.cleaned_data.get('ulice_cp'),
                    'mesto': self.cleaned_data.get('mesto'),
                    'psc': self.cleaned_data.get('psc'),
                    'is_premium': is_premium,
                    'premium_do': premium_do,
                    'pouzity_kod': final_kod,
                }
            )
        return user


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    telefon = forms.CharField(required=False)
    ulice_cp = forms.CharField(required=False, label="Ulice a č.p.")
    mesto = forms.CharField(required=False, label="Město")
    psc = forms.CharField(required=False, label="PSČ")

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profil'):
            self.fields['telefon'].initial = self.instance.profil.telefon
            self.fields['ulice_cp'].initial = self.instance.profil.ulice_cp
            self.fields['mesto'].initial = self.instance.profil.mesto
            self.fields['psc'].initial = self.instance.profil.psc
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profil = user.profil
            profil.telefon = self.cleaned_data.get('telefon')
            profil.ulice_cp = self.cleaned_data.get('ulice_cp')
            profil.mesto = self.cleaned_data.get('mesto')
            profil.psc = self.cleaned_data.get('psc')
            profil.save()
        return user


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


class ProfilUpdateForm(forms.ModelForm):
    class Meta:
        model = ProfilMajitele
        fields = ['telefon', 'ulice_cp', 'mesto', 'psc', 'pouzity_kod']
        widgets = {
            'pouzity_kod': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'pouzity_kod':
                field.widget.attrs.update({'class': 'form-control'})


class PlemenoForm(forms.ModelForm):
    class Meta:
        model = Plemeno
        fields = ['nazev', 'ikona', 'kategorie']