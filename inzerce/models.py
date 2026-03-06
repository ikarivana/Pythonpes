from django.db import models
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from PIL import Image
import os
import io

# Podpora pro iPhony
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass


class Inzerat(models.Model):
    # ROZŠÍŘENÉ KATEGORIE (pro psy i kočky)
    KATEGORIE_CHOICES = [
        ('zvirata', 'Zvířata k adopci / prodeji'),
        ('kryti', 'Krytí / Chov'),
        ('potreby', 'Potřeby a vybavení'),
        ('krmivo', 'Krmivo a pamlsky'),
        ('sluzby', 'Nabídka služeb (hlídání, venčení)'),
        ('ztraty', 'Ztráty a nálezy'),
        ('ostatni', 'Ostatní'),
    ]

    KRAJE_CHOICES = [
        ('PHA', 'Praha'), ('STC', 'Středočeský'), ('JHC', 'Jihočeský'),
        ('PLK', 'Plzeňský'), ('KVK', 'Karlovarský'), ('ULK', 'Ústecký'),
        ('LBK', 'Liberecký'), ('HKK', 'Královéhradecký'), ('PAK', 'Pardubický'),
        ('VYS', 'Vysočina'), ('JMK', 'Jihomoravský'), ('OLK', 'Olomoucký'),
        ('ZLK', 'Zlínský'), ('MSK', 'Moravskoslezský'),
    ]

    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    titulek = models.CharField(max_length=200, verbose_name="Titulek inzerátu")
    kategorie = models.CharField(max_length=20, choices=KATEGORIE_CHOICES, verbose_name="Kategorie")
    text = models.TextField(verbose_name="Popis")
    cena = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Cena (Kč)")

    # Lokalita
    kraj = models.CharField(max_length=3, choices=KRAJE_CHOICES, verbose_name="Kraj", default='PHA')
    mesto = models.CharField(max_length=100, verbose_name="Město / Lokalita")

    # Kontakt
    telefon = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    zobrazit_telefon = models.BooleanField(default=True, verbose_name="Zobrazit telefon")
    zobrazit_email = models.BooleanField(default=True, verbose_name="Zobrazit email")
    email_kontakni = models.EmailField(max_length=254, verbose_name="Kontaktní email", blank=True)

    # Média
    obrazek = models.ImageField(upload_to='inzeraty/obrazky/', null=True, blank=True, verbose_name="Hlavní fotografie")
    video = models.FileField(upload_to='inzeraty/videa/', null=True, blank=True, verbose_name="Video")

    vytvoreno = models.DateTimeField(auto_now_add=True)
    aktivni = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Inzerát"
        verbose_name_plural = "Inzeráty"
        ordering = ['-vytvoreno']

    def __str__(self):
        return f"{self.titulek} ({self.get_kategorie_display()})"

    def _convert_heic_to_jpg(self, image_field):
        """Pomocná metoda pro převod iPhoních fotek"""
        if not image_field:
            return

        extension = os.path.splitext(image_field.name)[1].lower()
        if extension in ['.heic', '.heif']:
            img = Image.open(image_field)
            rgb_img = img.convert('RGB')
            output = io.BytesIO()
            rgb_img.save(output, format='JPEG', quality=85)
            output.seek(0)
            new_name = os.path.splitext(image_field.name)[0] + ".jpg"
            image_field.save(new_name, ContentFile(output.read()), save=False)

    def save(self, *args, **kwargs):
        # Převod hlavní fotky
        if self.obrazek:
            self._convert_heic_to_jpg(self.obrazek)
        super().save(*args, **kwargs)


class InzeratFoto(models.Model):
    inzerat = models.ForeignKey(Inzerat, related_name='galerie', on_delete=models.CASCADE)
    foto = models.ImageField(upload_to='inzeraty/galerie/', verbose_name="Další fotografie")

    def save(self, *args, **kwargs):
        # Převod fotek v galerii
        if self.foto:
            # Tady musíme použít podobnou logiku jako u Inzerátu
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