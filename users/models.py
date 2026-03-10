from datetime import timedelta, date, datetime
from io import BytesIO

import qrcode
from django.core.files import File
from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify


class PromoKod(models.Model):
    kod = models.CharField(max_length=50, unique=True, verbose_name="Promo kód")
    pocet_dni = models.IntegerField(default=30, verbose_name="Počet dní premia")
    je_aktivni = models.BooleanField(default=True)
    poznamka = models.CharField(max_length=200, blank=True, verbose_name="Poznámka (např. útulek)")

    def __str__(self):
        return f"{self.kod} ({self.pocet_dni} dní)"


class ProfilMajitele(models.Model):
    uzivatel = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil')
    telefon = models.CharField(max_length=20, blank=True)
    ulice_cp = models.CharField(max_length=255, blank=True, verbose_name="Ulice a č.p.")
    mesto = models.CharField(max_length=100, blank=True, verbose_name="Město")
    psc = models.CharField(max_length=10, blank=True, verbose_name="PSČ")

    is_premium = models.BooleanField(default=False)
    premium_do = models.DateField(null=True, blank=True)

    # NOVÉ POLE PRO STATISTIKY
    pouzity_kod = models.CharField(max_length=50, blank=True, null=True, verbose_name="Použitý promo kód")

    @property
    def is_cat_person(self):
        """Bezpečná kontrola pro barvy v base.html"""
        try:
            # Spočítáme zvířata přes related_name='psi'
            pocet = self.psi.count()
            if pocet == 1:
                prvni = self.psi.first()
                return prvni and prvni.druh == 'kocka'
            return False
        except:
            return False


# --- MODEL PSA ---
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

    # Základní info
    cip = models.CharField(max_length=50, blank=True, null=True)
    fotka = models.ImageField(upload_to='profily_psu/', blank=True, null=True)
    foto_rotace = models.IntegerField(default=0)  # Ukládá úhly 0, 90, 180, 270
    vaha = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    datum_narozeni = models.DateField(null=True, blank=True)

    # Rodokmen a RTG
    otec_manualni = models.CharField(max_length=200, blank=True, null=True)
    matka_manualni = models.CharField(max_length=200, blank=True, null=True)
    chovna_stanice = models.CharField(max_length=200, blank=True, null=True)
    rtg_hd = models.CharField(max_length=50, blank=True, null=True)
    rtg_ed = models.CharField(max_length=50, blank=True, null=True)
    rtg_pater = models.CharField(max_length=100, blank=True, null=True)
    bonitace = models.TextField(blank=True, null=True)

    # QR a SOS stav
    qr_kod = models.ImageField(upload_to='qr_kody/', blank=True, null=True)
    je_ztraceny = models.BooleanField(default=False)

    # Aktuální prevence (to, co vidíme na kartě zdraví)
    posledni_ockovani = models.DateField(null=True, blank=True)
    posledni_odcerveni = models.DateField(null=True, blank=True)
    posledni_klistata = models.DateField(null=True, blank=True)

    # --- PŘIDANÉ METODY PRO ŠABLONU ---
    @property
    def vek(self):
        if not self.datum_narozeni:
            return "Nezadáno"

        today = date.today()
        # Rozdíl v letech
        years = today.year - self.datum_narozeni.year - (
                (today.month, today.day) < (self.datum_narozeni.month, self.datum_narozeni.day)
        )

        if years >= 1:
            if years == 1:
                return f"{years} rok"
            elif 1 < years < 5:
                return f"{years} roky"
            else:
                return f"{years} let"
        else:
            # Výpočet měsíců
            months = (today.year - self.datum_narozeni.year) * 12 + today.month - self.datum_narozeni.month
            if today.day < self.datum_narozeni.day:
                months -= 1
            months = max(0, months)

            if months == 1:
                return f"{months} měsíc"
            elif 1 < months < 5:
                return f"{months} měsíce"
            else:
                return f"{months} měsíců"

    @property
    def pristi_ockovani(self):
        """
        Vrátí buď konkrétní naplánované datum z historie očkování,
        nebo automaticky 1 rok od posledního očkování.
        """
        # 1. Zkusíme najít nejbližší budoucí termín z historie (pro štěňata)
        planovane = self.vsechna_ockovani.filter(datum_pristi_navstevy__gt=date.today()).order_by(
            'datum_pristi_navstevy').first()
        if planovane:
            return planovane.datum_pristi_navstevy

        # 2. Pokud není plán, použijeme tvou logiku + 1 rok
        if self.posledni_ockovani:
            return self.posledni_ockovani + timedelta(days=365)
        return None

    @property
    def pristi_odcerveni(self):
        if self.posledni_odcerveni:
            try:
                # Kočka 92 dní, pes 182 dní
                dny = 92 if self.druh == 'kocka' else 182
                # Musí zde být posledni_odcerveni!
                return self.posledni_odcerveni + timedelta(days=dny)
            except Exception:
                return None
        return None
    @property
    def pristi_klistata(self):
        """
        Vypočítá datum od poslední ochrany.
        Většina spot-onů/tablet trvá 1-3 měsíce (90 dní).
        """
        if self.posledni_klistata:
            return self.posledni_klistata + timedelta(days=90)
        return None

    # Stav
    vytvoreno = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.jmeno

    def save(self, *args, **kwargs):
        # 1. První uložení pro získání ID (pokud je nový)
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # 2. Generujeme QR kód pouze pokud pole qr_kod ZEJE PRÁZDNOTOU
        if not self.qr_kod:
            try:
                # URL odkazuje na detail psa (napořád stejné díky ID)
                qr_url = f"https://epes.online/pes/{self.id}/"

                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(qr_url)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")
                canvas = BytesIO()
                img.save(canvas, format='PNG')
                canvas.seek(0)

                fname = f'qr_pes_{self.id}.png'
                # save=False je důležité, abychom nezavolali save() znovu
                self.qr_kod.save(fname, File(canvas), save=False)

                # 3. Uložíme pouze pole qr_kod pomocí update_fields
                # Tím zabráníme nekonečné smyčce
                super(Pes, self).save(update_fields=['qr_kod'])
            except Exception as e:
                print(f"Chyba při generování QR: {e}")

class Ockovani(models.Model):
    pes = models.ForeignKey(Pes, on_delete=models.CASCADE, related_name='vsechna_ockovani')
    datum_ockovani = models.DateField()
    nazev_vakciny = models.CharField(max_length=200)
    poznamka = models.TextField(blank=True)
    datum_pristi_navstevy = models.DateField(null=True, blank=True)


    def __str__(self):
        return f"{self.nazev_vakciny} - {self.pes.jmeno}"


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
    pes = models.ForeignKey(Pes, on_delete=models.CASCADE, related_name='uspechy')
    nazev = models.CharField(max_length=200)
    typ = models.CharField(max_length=100, blank=True)  # např. Výstava, Zkouška
    datum = models.DateField(null=True, blank=True)


class ZdravotniZaznam(models.Model):
    pes = models.ForeignKey(Pes, on_delete=models.CASCADE, related_name='zaznamy_zdravi')
    titulek = models.CharField(max_length=200)
    popis = models.TextField()
    datum_vytvoreni = models.DateTimeField(auto_now_add=True)


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
    typ = models.CharField(max_length=20)  # 'like', 'komentar'

    # --- OPRAVA: Použití názvu třídy Prispevek ---
    prispevek = models.ForeignKey('Prispevek', on_delete=models.CASCADE, null=True, blank=True)
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