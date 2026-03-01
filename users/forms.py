from datetime import timedelta, date
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
# --- OPRAVA: Ujistěte se, že všechny importy existují v models.py ---
from .models import Pes, Ockovani, Prispevek, Plemeno, ProfilMajitele, PromoKod


# --- POMOCNÉ TŘÍDY ---

class CzechClearableFileInput(forms.ClearableFileInput):
    """Upravuje popisky u nahrávání souborů do češtiny"""
    clear_checkbox_label = 'Smazat aktuální soubor'
    initial_text = 'Aktuální'
    input_text = 'Změnit'


# --- 1. FORMULÁŘ PRO PSA ---
class PesForm(forms.ModelForm):
    # --- OPRAVA: Odstraněna duplicitní definice 'fotka',
    # pokud je již definována v modelu Pes. Pokud není, ponechte zde. ---

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
            'jmeno', 'rasa', 'datum_narozeni', 'cip', 'vaha', 'fotka', 'video',
            'posledni_ockovani', 'posledni_odcerveni', 'posledni_klistata', 'typ_ochrany_klistata',
            'rtg_hd', 'rtg_ed', 'rtg_pater', 'zdravotni_testy', 'genetika_dna', 'popis',
            'bonitace', 'otec_manualni', 'matka_manualni'
        ]

        widgets = {
            'datum_narozeni': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'posledni_ockovani': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'posledni_odcerveni': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'posledni_klistata': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'typ_ochrany_klistata': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Obojek / Pipeta'}),
            'popis': forms.Textarea(attrs={'rows': 3}),
            'zdravotni_testy': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Např. Lokus S, DM...'}),
            'fotka': forms.FileInput(attrs={'accept': 'image/*'}),
            'vaha': forms.NumberInput(attrs={'step': '0.1', 'placeholder': 'Např. 12.5'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Hromadné přidání CSS tříd
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control custom-brown-input'})

        # Omezení pro FREE uživatele (kontrola is_premium)
        if self.request and not (self.request.user.is_staff or self.request.user.profil.is_premium):
            # Seznam polí, kam NECHCEME nechat uživatele psát
            premium_pole = ['rtg_hd', 'rtg_ed', 'genetika_dna', 'zdravotni_testy', 'rtg_pater']

            for field_name in premium_pole:
                if field_name in self.fields:
                    # 1. Zamezí zápisu a výběru (políčko zešedne)
                    self.fields[field_name].disabled = True
                    # 2. Přidá textovou nápovědu pod políčko
                    self.fields[field_name].help_text = "🔒 Pouze pro ALFA pány"
                    # 3. Přidá informaci přímo do vnitřku pole pro lepší UX
                    self.fields[field_name].widget.attrs['placeholder'] = "Dostupné v Premium verzi"

# --- 2. FORMULÁŘE PRO UŽIVATELE ---

class ExtendedRegistrationForm(UserCreationForm):
    """Formulář pro registraci s rozšířenými poli o profil, adresu a promo kód"""
    email = forms.EmailField(required=True, label="E-mail")
    telefon = forms.CharField(required=False, label="Telefon")
    ulice_cp = forms.CharField(required=False, label="Ulice a č.p.")
    mesto = forms.CharField(required=False, label="Město")
    psc = forms.CharField(required=False, label="PSČ")
    promo_kod = forms.CharField(
        required=False,
        label="Promo kód (volitelné)",
        widget=forms.TextInput(attrs={'placeholder': 'Máš kód? Např. UTULEK'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Přidání CSS třídy pro Bootstrap
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()

            # Logika pro výpočet Premia z kódu
            kod_text = self.cleaned_data.get('promo_kod', '').strip()
            is_premium = False
            premium_do = None
            final_kod = None

            if kod_text:
                try:
                    # Hledáme kód (case-insensitive - nezáleží na velkých/malých písmenech)
                    pkod = PromoKod.objects.get(kod__iexact=kod_text, je_aktivni=True)
                    is_premium = True
                    premium_do = date.today() + timedelta(days=pkod.pocet_dni)
                    final_kod = pkod.kod.upper()
                except PromoKod.DoesNotExist:
                    final_kod = f"NEPLATNÝ: {kod_text}"

            # Vytvoříme nebo aktualizujeme profil
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
    """Formulář pro aktualizaci profilu v nastavení"""
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
        # Naplnění profilových polí daty z modelu ProfilMajitele
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
            # Uložení změn do modelu profilu
            profil = user.profil
            profil.telefon = self.cleaned_data.get('telefon')
            profil.ulice_cp = self.cleaned_data.get('ulice_cp')
            profil.mesto = self.cleaned_data.get('mesto')
            profil.psc = self.cleaned_data.get('psc')
            profil.save()
        return user

# --- 3. OSTATNÍ FORMULÁŘE (Sociální síť a zdraví) ---

class PrispevekForm(forms.ModelForm):
    class Meta:
        model = Prispevek
        fields = ['text', 'obrazek', 'video']
        widgets = {
            'text': forms.Textarea(attrs={'placeholder': 'Co je nového?'}),
        }


class PlemenoForm(forms.ModelForm):
    class Meta:
        model = Plemeno
        fields = ['nazev', 'ikona', 'kategorie']  # PŘIDÁNO: ikona a kategorie z našeho modelu!


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