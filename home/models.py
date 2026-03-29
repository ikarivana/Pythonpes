from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import User



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

    class Meta:
        ordering = ['-vytvoreno'] # Nejnovější nahoře

    def __str__(self):
        return f"{self.uzivatel.username} - {self.sluzba.nazev} ({self.hvezdy}*)"


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