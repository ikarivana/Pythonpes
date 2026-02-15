from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Sluzba(models.Model):
    TYPY_SLUZEB = [
        ('nebezpeci', '⚠️ NEBEZPEČÍ (Návnady, střepy, apod.)'),
        ('obchod', 'Obchod pro psy'),
        ('veterina', 'Veterinář'),
        ('strihani', 'Stříhání psů / Salon'),
        ('hotel', 'Psí hotel'),
        ('wellness', 'Wellness pro psy'),
        ('cvicak', 'Cvičiště'),
        ('utulek', 'Útulek'),
        ('chovna_stanice', 'Chovná stanice'),
    ]

    vlastnik = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moje_sluzby', null=True, blank=True)
    nazev = models.CharField(max_length=200)
    typ = models.CharField(max_length=20, choices=TYPY_SLUZEB)
    adresa = models.CharField(max_length=300)
    popis = models.TextField(blank=True)
    web = models.URLField(blank=True)
    telefon = models.CharField(max_length=20, blank=True)
    schvaleno = models.BooleanField(default=False, verbose_name="Schváleno administrátorem")

    # Pole pro komunitní moderování
    potvrzeni_minus = models.IntegerField(default=0, verbose_name="Nahlášení jako neaktuální")

    lat = models.FloatField(verbose_name="Zeměpisná šířka")
    lon = models.FloatField(verbose_name="Zeměpisná délka")
    vytvoreno = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nazev} ({self.get_typ_display()})"

    def je_aktivni(self):
        """Logika pro automatické mizení nebezpečí"""
        if self.typ == 'nebezpeci':
            # Nebezpečí zmizí po 24 hodinách nebo po 3 nahlášeních
            limit = timezone.now() - timedelta(hours=24)
            return self.vytvoreno > limit and self.potvrzeni_minus < 3
        return True  # Ostatní služby jsou aktivní stále (pokud je nesmažeš)

# home/models.py

class KontaktniZprava(models.Model):
    jmeno = models.CharField(max_length=100, verbose_name="Jméno")
    email = models.EmailField(verbose_name="E-mail")
    predmet = models.CharField(max_length=200, verbose_name="Předmět")
    zprava = models.TextField(verbose_name="Zpráva")
    vytvoreno = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Zpráva od {self.jmeno} - {self.predmet}"