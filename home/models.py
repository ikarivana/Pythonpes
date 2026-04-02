import os
from io import BytesIO

import pillow_heif
from PIL import Image
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import User

pillow_heif.register_heif_opener()

class Sluzba(models.Model):
    TYPY_SLUZEB = [
        ('ztrata', '🚨 ZTRACENÉ ZVÍŘE'),
        ('nebezpeci', '⚠️ NEBEZPEČÍ (Návnady, střepy, apod.)'),
        ('obchod', '🛒 Obchod pro psy'),
        ('veterina', '🏥 Veterinář'),
        ('strihani', '✂️ Stříhání psů / Salon'),
        ('hotel', '🏠 Psí hotel'),
        ('wellness', '🛁 Wellness pro psy'),
        ('cvicak', '🎾 Cvičiště'),
        ('utulek', '🐕 Útulek'),
        ('chovna_stanice', '🧬 Chovná stanice'),
        ('gastro', 'Kavárny a restaurace ☕'),
    ]

    vlastnik = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='moje_sluzby', null=True, blank=True)
    nazev = models.CharField(max_length=200)
    typ = models.CharField(max_length=20, choices=TYPY_SLUZEB)
    adresa = models.CharField(max_length=300)
    popis = models.TextField(blank=True)
    web = models.URLField(blank=True)
    telefon = models.CharField(max_length=20, blank=True)

    # Pro schvalování v adminu
    schvaleno = models.BooleanField(default=False, verbose_name="Schváleno administrátorem")

    # Pro komunitní hlášení
    potvrzeni_minus = models.IntegerField(default=0, verbose_name="Nahlášení jako neaktivní")

    # Souřadnice pro mapu
    lat = models.FloatField(verbose_name="Zeměpisná šířka", null=True, blank=True)
    lon = models.FloatField(verbose_name="Zeměpisná délka", null=True, blank=True)

    vytvoreno = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Pokud jde o SOS kategorii, schválíme ji automaticky hned při uložení
        if self.typ in ['ztrata', 'nebezpeci', 'navnada']:
            self.schvaleno = True
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Služba"
        verbose_name_plural = "Služby"

    def __str__(self):
        return f"{self.nazev} ({self.get_typ_display()})"


class Recenze(models.Model):
    sluzba = models.ForeignKey('Sluzba', on_delete=models.CASCADE, related_name='recenze_set')
    uzivatel = models.ForeignKey(User, on_delete=models.CASCADE)
    hvezdy = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField(max_length=1000)
    vytvoreno = models.DateTimeField(auto_now_add=True)

    # NOVÁ POLE PRO MÉDIA
    media_soubor = models.FileField(upload_to='recenze_media/', null=True, blank=True)

    def save(self, *args, **kwargs):
        # Kontrola, zda máme soubor a zda je to HEIC
        if self.media_soubor and hasattr(self.media_soubor, 'name'):
            ext = os.path.splitext(self.media_soubor.name)[1].lower()

            if ext in ['.heic', '.heif']:
                # Otevření HEIC obrázku
                img = Image.open(self.media_soubor)

                # Konverze do RGB (HEIC je často v jiném barevném prostoru)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Příprava bufferu pro uložení JPEG
                output = BytesIO()
                img.save(output, format='JPEG', quality=90)  # Snížíme lehce kvalitu pro úsporu místa
                output.seek(0)

                # Změna názvu souboru na .jpg
                new_name = os.path.splitext(self.media_soubor.name)[0] + ".jpg"

                # Nahrazení původního souboru zkonvertovaným JPEGem
                self.media_soubor.save(new_name, ContentFile(output.read()), save=False)

        super().save(*args, **kwargs)

    @property
    def je_video(self):
        if not self.media_soubor:
            return False
        ext = os.path.splitext(self.media_soubor.name)[1].lower()
        return ext in ['.mp4', '.mov', '.avi', '.webm']

class KontaktniZprava(models.Model):
    jmeno = models.CharField(max_length=100, verbose_name="Jméno")
    email = models.EmailField(verbose_name="E-mail")
    predmet = models.CharField(max_length=200, verbose_name="Předmět")
    zprava = models.TextField(verbose_name="Zpráva")
    vytvoreno = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kontaktní zpráva"
        verbose_name_plural = "Kontaktní zprávy"

    def __str__(self):
        return f"Zpráva od {self.jmeno} - {self.predmet}"