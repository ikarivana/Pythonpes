from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import os
from PIL import Image
import io
from django.core.files.base import ContentFile

# Pokud používáš iPhony, je dobré mít nainstalováno: pip install pillow-heif
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

class Inzerat(models.Model):
    KATEGORIE_CHOICES = [
        ('stenata', 'Štěňata'),
        ('psi_feny', 'Dospělí psi a feny'),
        ('kryti', 'Krytí / Chov'),
        ('potreby', 'Potřeby a hračky'),
        ('krmivo', 'Krmivo'),
        ('oblecky', 'Oblečky'),
        ('ztraty', 'Ztráty a nálezy'),
    ]

    KRAJE_CHOICES = [
        ('PHA', 'Praha'),
        ('STC', 'Středočeský'),
        ('JHC', 'Jihočeský'),
        ('PLK', 'Plzeňský'),
        ('KVK', 'Karlovarský'),
        ('ULK', 'Ústecký'),
        ('LBK', 'Liberecký'),
        ('HKK', 'Královéhradecký'),
        ('PAK', 'Pardubický'),
        ('VYS', 'Vysočina'),
        ('JMK', 'Jihomoravský'),
        ('OLK', 'Olomoucký'),
        ('ZLK', 'Zlínský'),
        ('MSK', 'Moravskoslezský'),
    ]

    kraj = models.CharField(
        max_length=3,
        choices=KRAJE_CHOICES,
        verbose_name="Kraj",
        default='PHA'
    )
    mesto = models.CharField(max_length=100, verbose_name="Město")

    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    kategorie = models.CharField(max_length=20, choices=KATEGORIE_CHOICES, verbose_name="Kategorie")
    titulek = models.CharField(max_length=200, verbose_name="Titulek inzerátu")
    text = models.TextField(verbose_name="Popis")
    cena = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Cena (Kč)")
    mesto = models.CharField(max_length=100, verbose_name="Město / Lokalita")
    telefon = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    zobrazit_telefon = models.BooleanField(default=True, verbose_name="Zobrazit telefon v inzerátu")
    zobrazit_email = models.BooleanField(default=True, verbose_name="Zobrazit email v inzerátu")
    email_kontakni = models.EmailField(max_length=254, verbose_name="Kontaktní email", blank=True)

    # Hlavní náhledový obrázek
    obrazek = models.ImageField(upload_to='inzeraty/obrazky/', null=True, blank=True, verbose_name="Hlavní fotografie")

    # Video
    video = models.FileField(upload_to='inzeraty/videa/', null=True, blank=True, verbose_name="Video")

    vytvoreno = models.DateTimeField(auto_now_add=True)
    aktivni = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Inzerát"
        verbose_name_plural = "Inzeráty"

    def __str__(self):
        return f"{self.titulek} ({self.get_kategorie_display()})"

    def save(self, *args, **kwargs):
        # 1. Ošetření HEIC/HEIF formátu a převod na JPEG
        if self.obrazek:
            extension = os.path.splitext(self.obrazek.name)[1].lower()
            if extension in ['.heic', '.heif']:
                img = Image.open(self.obrazek)
                # Převod do RGB (nutné pro JPEG)
                rgb_img = img.convert('RGB')

                # Uložení do paměti jako JPEG
                output = io.BytesIO()
                rgb_img.save(output, format='JPEG', quality=85)
                output.seek(0)

                # Změna názvu souboru na .jpg
                new_name = os.path.splitext(self.obrazek.name)[0] + ".jpg"
                self.obrazek = ContentFile(output.read(), name=new_name)

        super().save(*args, **kwargs)

# NOVÝ MODEL PRO DALŠÍ FOTKY
class InzeratFoto(models.Model):
    inzerat = models.ForeignKey(Inzerat, related_name='galerie', on_delete=models.CASCADE)
    foto = models.ImageField(upload_to='inzeraty/galerie/', verbose_name="Další fotografie")

    class Meta:
        verbose_name = "Fotografie z galerie"
        verbose_name_plural = "Fotografie z galerie"

    def save(self, *args, **kwargs):
        if self.foto:
            extension = os.path.splitext(self.foto.name)[1].lower()
            if extension in ['.heic', '.heif']:
                img = Image.open(self.foto)
                rgb_img = img.convert('RGB')
                output = io.BytesIO()
                rgb_img.save(output, format='JPEG', quality=85)
                output.seek(0)
                new_name = os.path.splitext(self.foto.name)[0] + ".jpg"
                self.foto = ContentFile(output.read(), name=new_name)
        super().save(*args, **kwargs)