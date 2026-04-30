from datetime import timedelta, date, datetime
from io import BytesIO

import qrcode
from django.core.files import File
from django.db import models
from django.contrib.auth.models import User
from django.http import request
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils import timezone

import pes


class PromoKod(models.Model):
    kod = models.CharField(max_length=50, unique=True, verbose_name="Promo kód")
    pocet_dni = models.IntegerField(default=30, verbose_name="Počet dní premia")
    je_aktivni = models.BooleanField(default=True)
    poznamka = models.CharField(max_length=200, blank=True, verbose_name="Poznámka (např. útulek)")

    def __str__(self):
        return f"{self.kod} ({self.pocet_dni} dní)"


from django.db import models
from django.contrib.auth.models import User
from PIL import Image, ExifTags  # Nutné pro práci s obrázky


class ProfilMajitele(models.Model):
    uzivatel = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil')
    # Přidáno pole pro fotku:
    fotka = models.ImageField(upload_to='profily/', null=True, blank=True, verbose_name="Profilová fotka")

    is_premium = models.BooleanField(default=False)
    premium_do = models.DateField(null=True, blank=True, verbose_name="Premium platné do")
    ulice_cp = models.CharField(max_length=255, blank=True, verbose_name="Ulice a č.p.")
    mesto = models.CharField(max_length=100, blank=True, verbose_name="Město")
    psc = models.CharField(max_length=10, blank=True, verbose_name="PSČ")
    telefon = models.CharField(max_length=20, blank=True)
    souhlas_podminky = models.BooleanField(default=False)

    def __str__(self):
        return f"Profil: {self.uzivatel.username}"

    def save(self, *args, **kwargs):
        # Nejdříve uložíme soubor standardně
        super().save(*args, **kwargs)

        if self.fotka:
            filepath = self.fotka.path
            img = Image.open(filepath)

            # Automatické otočení podle EXIF dat
            try:
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break

                exif = dict(img._getexif().items())

                if exif[orientation] == 3:
                    img = img.rotate(180, expand=True)
                elif exif[orientation] == 6:
                    img = img.rotate(270, expand=True)
                elif exif[orientation] == 8:
                    img = img.rotate(90, expand=True)

                img.save(filepath)
            except (AttributeError, KeyError, IndexError):
                # Fotka nemá EXIF data (např. screenshot) nebo je již v pořádku
                pass

# --- 1. MODEL PSA ---
class Pes(models.Model):
    DRUH_CHOICES = [('pes', 'Pes'), ('kocka', 'Kočka')]
    druh = models.CharField(max_length=10, choices=DRUH_CHOICES, default='pes')
    majitel = models.ForeignKey(ProfilMajitele, on_delete=models.CASCADE, related_name='psi')
    jmeno = models.CharField(max_length=100)
    rasa = models.CharField(max_length=100)

    # SOS Kontakty
    kontaktni_jmeno = models.CharField(max_length=100)
    kontaktni_telefon = models.CharField(max_length=20)
    kontaktni_email = models.EmailField()
    adresa_pro_darky = models.TextField(blank=True, null=True)
    lat = models.FloatField(blank=True, null=True, verbose_name="Zeměpisná šířka")
    lon = models.FloatField(blank=True, null=True, verbose_name="Zeměpisná délka")
    je_u_nalezece = models.BooleanField(default=False)

    # Základní info
    cip = models.CharField(max_length=50, blank=True, null=True)
    fotka = models.ImageField(upload_to='profily_psu/', blank=True, null=True)
    foto_rotace = models.IntegerField(default=0)
    vaha = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    datum_narozeni = models.DateField(null=True, blank=True)
    hlavni_veterinar_nazev = models.CharField(max_length=200, blank=True, null=True, verbose_name="Hlavní veterina")
    hlavni_veterinar_telefon = models.CharField(max_length=20, blank=True, null=True,
                                                verbose_name="Telefon na veterinu")

    # Rodokmen a RTG
    otec_manualni = models.CharField(max_length=200, blank=True, null=True)
    matka_manualni = models.CharField(max_length=200, blank=True, null=True)
    chovna_stanice = models.CharField(max_length=200, blank=True, null=True)
    rtg_hd = models.CharField(max_length=50, blank=True, null=True)
    rtg_ed = models.CharField(max_length=50, blank=True, null=True)
    rtg_pater = models.CharField(max_length=100, blank=True, null=True)
    bonitace = models.TextField(blank=True, null=True)

    # Nahrání rodokmenu v PDF
    rodokmen_pdf = models.FileField(upload_to='rodokmeny/', blank=True, null=True, verbose_name="Rodokmen v PDF")

    # QR a SOS stav
    qr_kod = models.ImageField(upload_to='qr_kody/', blank=True, null=True)
    je_ztraceny = models.BooleanField(default=False)

    # Detailní texty (pro detail psa a pro nálezce)
    zdravotni_poznamky = models.TextField(blank=True, null=True, verbose_name="Alergie a lékařské poznámky")
    popis = models.TextField(blank=True, null=True, verbose_name="Povaha a instrukce pro nálezce")

    # Aktuální prevence
    posledni_ockovani = models.DateField(null=True, blank=True)
    posledni_odcerveni = models.DateField(null=True, blank=True)
    posledni_klistata = models.DateField(null=True, blank=True)
    vytvoreno = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.jmeno

    class Meta:
        verbose_name = "Pes"
        verbose_name_plural = "Psi"

    @property
    def je_premium(self):
        try:
            profil = self.majitel
            if profil.is_premium:
                if profil.premium_do:
                    return profil.premium_do >= date.today()
                return True
            return False
        except AttributeError:
            return False

    def je_prvni_v_poradi(self):
        # Najde úplně první zvíře stejného druhu (pes/kočka), které si majitel registroval
        prvni = Pes.objects.filter(majitel=self.majitel, druh=self.druh).order_by('vytvoreno').first()
        return prvni and prvni.id == self.id

    @property
    def vek(self):
        if not self.datum_narozeni:
            return "Nezadáno"

        today = date.today()

        # Výpočet celých let
        years = today.year - self.datum_narozeni.year - (
                    (today.month, today.day) < (self.datum_narozeni.month, self.datum_narozeni.day))

        # Pokud je zvířeti 1 rok a více, vrátíme roky
        if years >= 1:
            return f"{years} let"

        # Pokud je mladší než 1 rok, spočítáme měsíce
        months = (today.year - self.datum_narozeni.year) * 12 + today.month - self.datum_narozeni.month
        if today.day < self.datum_narozeni.day:
            months -= 1

        # Ošetření pro případ, že je zvíře narozené dnes nebo v budoucnu
        if months <= 0:
            return "Novorozeně"

        return f"{months} měs."

    # bing
    def get_absolute_url(self):
        return reverse('detail_psa', kwargs={'pes_id': self.id})

    def save(self, *args, **kwargs):
        # 1. Nejdřív uložíme základní data
        super().save(*args, **kwargs)

        # 2. QR kód vygenerujeme jen, pokud pole qr_kod v DB zatím není
        if not self.qr_kod:
            try:
                qr_url = f"https://epes.online/users/pes/{self.id}/"
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(qr_url)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")
                canvas = BytesIO()
                img.save(canvas, format='PNG')
                canvas.seek(0)

                filename = f'qr_pes_{self.id}.png'

                # save=False je ZÁSADNÍ - uloží soubor, ale nespustí znovu save()
                self.qr_kod.save(filename, File(canvas), save=False)

                # Tichý zápis do DB přes update (nepouští signály ani save())
                self.__class__.objects.filter(pk=self.pk).update(qr_kod=self.qr_kod.name)

            except Exception as e:
                print(f"Chyba při tvorbě QR: {e}")

# --- 2. MODEL PRO VÝSTAVY ---
class Vystava(models.Model):
    pes = models.ForeignKey(Pes, on_delete=models.CASCADE, related_name='vystavy_seznam')
    datum = models.DateField()
    nazev = models.CharField(max_length=200, verbose_name="Název výstavy")
    misto = models.CharField(max_length=200, blank=True)
    oceneni = models.CharField(max_length=200, help_text="Např. V1, CAC, BOB")
    rozhodci = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ['-datum']

# --- 3. MODEL PRO VRHY ---
class Vrh(models.Model):
    rodic = models.ForeignKey(Pes, on_delete=models.CASCADE, related_name='potomci')
    datum_narozeni = models.DateField()
    oznaceni_vrhu = models.CharField(max_length=50, help_text="Např. Vrh A")
    pocet_psu = models.PositiveIntegerField(default=0)
    pocet_fen = models.PositiveIntegerField(default=0)
    druhy_rodic = models.CharField(max_length=200, help_text="Jméno partnera/partnerky")
    poznamka = models.TextField(blank=True)

    class Meta:
        ordering = ['-datum_narozeni']

# --- 4. MODEL OČKOVÁNÍ (Ten ti chyběl a admin ho hledal!) ---
class Ockovani(models.Model):
    pes = models.ForeignKey(Pes, on_delete=models.CASCADE, related_name='vsechna_ockovani')
    datum_ockovani = models.DateField()
    nazev_vakciny = models.CharField(max_length=200)
    poznamka = models.TextField(blank=True)
    datum_pristi_navstevy = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.nazev_vakciny} - {self.pes.jmeno}"

    class Meta:
        verbose_name = "Očkování"
        verbose_name_plural = "Očkování"

# --- GALERIE FOTEK ---
class GalerieFotka(models.Model):
    pes = models.ForeignKey(Pes, on_delete=models.CASCADE, related_name='galerie_fotky')
    obrazek = models.ImageField(upload_to='galerie_psu/')
    vytvoreno = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fotka v galerii"
        verbose_name_plural = "Galerie fotek"

# --- GALERIE VIDEÍ ---
class GalerieVideo(models.Model):
    pes = models.ForeignKey(Pes, on_delete=models.CASCADE, related_name='galerie_videa')
    video_soubor = models.FileField(upload_to='videa_psu/')
    vytvoreno = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videa"


# --- OSTATNÍ DOPLŇKY (Úspěchy, Zdraví) ---
class Uspech(models.Model):
    TYPY_AKCI = [
        ('vystava', 'Výstava'),
        ('zkouska', 'Zkouška / Bonitace'),
        ('sport', 'Sportovní výkon'),
    ]
    pes = models.ForeignKey(Pes, on_delete=models.CASCADE, related_name='uspechy')
    typ = models.CharField(max_length=20, choices=TYPY_AKCI, default='vystava')
    nazev = models.CharField(max_length=200)
    misto = models.CharField(max_length=200, blank=True, null=True)
    datum = models.DateField()
    oceneni = models.CharField(max_length=200) # Např. "Výborný 1, CAC"

    class Meta:
        ordering = ['-datum'] # Nejnovější úspěchy nahoře

# --- SOCIÁLNÍ SÍŤ ---
class Plemeno(models.Model):
    nazev = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    ikona = models.ImageField(upload_to='plemena_ikony/', blank=True)

    # Hodnoty: 'vystavy', 'lovecka', 'ostatni'
    kategorie = models.CharField(max_length=50, default='ostatni', db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nazev)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nazev} ({self.kategorie})"


class Prispevek(models.Model):
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    plemeno = models.ForeignKey(Plemeno, on_delete=models.CASCADE, related_name='prispevky_na_zed', null=True, blank=True)
    sekce_slug = models.CharField(max_length=100, db_index=True, blank=True)
    text = models.TextField()
    obrazek = models.ImageField(upload_to='prispevky/', blank=True, null=True)
    video = models.FileField(upload_to='videa/', blank=True, null=True)
    datum_pridani = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='libi_se_mi', blank=True)

    class Meta:
        ordering = ['-datum_pridani']

    def __str__(self):
        return f"Příspěvek od {self.autor.username}"


class Komentar(models.Model):
    # Odkaz na Prispevek, uvozovky jsou bezpečnější, pokud by byl Prispevek níže
    prispevek = models.ForeignKey('Prispevek', on_delete=models.CASCADE, related_name='komentare')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    datum_pridani = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['datum_pridani']


class Notifikace(models.Model):
    prijemce = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prijate_notifikace')
    odesilatel = models.ForeignKey(User, on_delete=models.CASCADE, related_name='odeslane_notifikace')

    # Rozšíříme o 'recenze' a 'moje_aktivita'
    typ = models.CharField(max_length=20)  # 'like', 'komentar', 'recenze', 'moje_aktivita'

    # Propojení na příspěvky ze zdi
    prispevek = models.ForeignKey('Prispevek', on_delete=models.CASCADE, null=True, blank=True)

    # --- NOVÉ: Propojení na služby (vHome / Mapa) ---
    # Předpokládám, že se tvůj model pro služby jmenuje 'Sluzba'
    sluzba = models.ForeignKey('home.Sluzba', on_delete=models.CASCADE, null=True, blank=True)

    # --- NOVÉ: Text pro "Moje aktivita" ---
    text = models.TextField(null=True, blank=True)
    # ---------------------------------------------

    precteno = models.BooleanField(default=False)
    datum_vytvoreni = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-datum_vytvoreni']

class Like(models.Model):
    uzivatel = models.ForeignKey(User, on_delete=models.CASCADE)
    prispevek = models.ForeignKey(Prispevek, on_delete=models.CASCADE)
    datum_pridani = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Zajistí, že uživatel může dát jeden lajk příspěvku jen jednou
        unique_together = ('uzivatel', 'prispevek')


class ZdravotniZaznam(models.Model):
    TYP_CHOICES = [
        ('ockovani', 'Očkování'),
        ('odcerveni', 'Odčervení'),
        ('vaha', 'Vážení'),
        ('paraziti', 'Klíšťata / Blechy'),
        ('kontrola', 'Lékařská kontrola'),
        ('urgentni', '🚨 Urgentní případ'),  # Přidáno pro SOS stavy
    ]
    pes = models.ForeignKey(Pes, on_delete=models.CASCADE, related_name='denik')
    datum = models.DateField()
    typ = models.CharField(max_length=20, choices=TYP_CHOICES)
    titulek = models.CharField(max_length=200, help_text="Např. název tablety nebo vakcíny")
    poznamka = models.TextField(blank=True, null=True, help_text="Zde dopíšeš léky nebo průběh kontroly")

    # NOVÉ: Možnost zadat jinou kliniku než hlavní
    klinika = models.CharField(max_length=200, blank=True, null=True, verbose_name="Ošetřující klinika")

    class Meta:
        ordering = ['-datum']

    def __str__(self):
        return f"{self.get_typ_display()} - {self.pes.jmeno} ({self.datum})"

    def save(self, *args, **kwargs):
        # ... tvoje stávající logika save (ockovani, odcerveni, vaha atd.) zůstává stejná ...
        super().save(*args, **kwargs)

        if self.typ == 'ockovani':
            self.pes.posledni_ockovani = self.datum
        elif self.typ == 'odcerveni':
            self.pes.posledni_odcerveni = self.datum
        elif self.typ == 'paraziti':
            self.pes.posledni_klistata = self.datum
        elif self.typ == 'vaha':
            try:
                import decimal
                self.pes.vaha = decimal.Decimal(str(self.titulek).replace(',', '.'))
            except:
                pass

        self.pes.save(update_fields=['posledni_ockovani', 'posledni_odcerveni', 'posledni_klistata', 'vaha'])
