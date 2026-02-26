from datetime import timedelta, date

from django.contrib.auth.models import User
from django.utils.text import slugify
import qrcode
from io import BytesIO
from django.core.files import File
from django.db import models


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


# --- MODEL PSA ---
class Pes(models.Model):
    majitel = models.ForeignKey(ProfilMajitele, on_delete=models.CASCADE, related_name='psi')
    jmeno = models.CharField(max_length=100)
    rasa = models.CharField(max_length=100)
    cip = models.CharField(max_length=50, blank=True)
    fotka = models.ImageField(upload_to='profily_psu/', blank=True, null=True)
    video = models.FileField(upload_to='videa_psu/', null=True, blank=True)
    popis = models.TextField(blank=True, null=True)
    otec_manualni = models.CharField(max_length=200, blank=True, null=True, verbose_name="Otec (jméno)")
    matka_manualni = models.CharField(max_length=200, blank=True, null=True, verbose_name="Matka (jméno)")
    datum_narozeni = models.DateField(null=True, blank=True, verbose_name="Datum narození")
    genetika_dna = models.TextField(blank=True, null=True)
    zdravotni_testy = models.TextField(blank=True, null=True, verbose_name="Zdravotní testy")
    bonitace = models.TextField(blank=True, null=True, verbose_name="Bonitace")
    rtg_pater = models.CharField(max_length=100, blank=True, null=True)
    typ_ochrany_klistata = models.CharField(max_length=100, blank=True, null=True)
    qr_kod = models.ImageField(upload_to='qr_kody/', blank=True, null=True)
    je_ztraceny = models.BooleanField(default=False)
    oblast_ztraty = models.CharField(max_length=255, verbose_name="Kde se pejsek ztratil?", null=True, blank=True)

    # Chovatelské údaje
    cislo_zapisu = models.CharField(max_length=100, blank=True, null=True)
    rtg_hd = models.CharField(max_length=50, blank=True, null=True)  # DKK
    rtg_ed = models.CharField(max_length=50, blank=True, null=True)  # DLK
    bonitace = models.TextField(blank=True, null=True)
    rodokmen = models.TextField(blank=True, null=True)
    chovna_stanice = models.CharField(max_length=200, blank=True, null=True)

    # Zdravotní prevence
    posledni_ockovani = models.DateField(null=True, blank=True)
    posledni_odcerveni = models.DateField(null=True, blank=True)
    posledni_klistata = models.DateField(null=True, blank=True)

    # --- PŘIDANÉ METODY PRO ŠABLONU ---
    @property
    def vek(self):
        if self.datum_narozeni:
            today = date.today()
            # Rozdíl v letech
            years = today.year - self.datum_narozeni.year - (
                    (today.month, today.day) < (self.datum_narozeni.month, self.datum_narozeni.day)
            )

            # Pokud je pejskovi 1 a více let
            if years >= 1:
                if years == 1:
                    return f"{years} rok"
                elif 1 < years < 5:
                    return f"{years} roky"
                else:
                    return f"{years} let"

            # Pokud je pejskovi méně než rok, počítáme měsíce
            else:
                months = (today.year - self.datum_narozeni.year) * 12 + today.month - self.datum_narozeni.month
                if today.day < self.datum_narozeni.day:
                    months -= 1

                # Zamezíme záporným měsícům u čerstvě narozených
                months = max(0, months)

                if months == 1:
                    return f"{months} měsíc"
                elif 1 < months < 5:
                    return f"{months} měsíce"
                else:
                    return f"{months} měsíců"

        return "Nezadáno"
    @property
    def pristi_ockovani(self):
        """Vypočítá datum za 1 rok od posledního očkování"""
        if self.posledni_ockovani:
            return self.posledni_ockovani + timedelta(days=365)
        return None

    @property
    def pristi_odcerveni(self):
        """Vypočítá datum za 6 měsíců (182 dní) od posledního odčervení"""
        if self.posledni_odcerveni:
            return self.posledni_odcerveni + timedelta(days=182)
        return None

    @property
    def pristi_klistata(self):
        """Vypočítá datum za 3 měsíce (90 dní) od poslední ochrany"""
        if self.posledni_klistata:
            return self.posledni_klistata + timedelta(days=90)
        return None

    # Stav
    je_ztraceny = models.BooleanField(default=False)
    vytvoreno = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.jmeno

    def save(self, *args, **kwargs):
        # Pokud pes ještě nemá ID (vytváří se nový), musíme ho nejdřív uložit
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # 2. Generujeme QR kód pouze pokud ještě neexistuje
        if not self.qr_kod:
            try:
                # Sjednoť URL s urls.py (buď /pes/ nebo /users/pes/)
                qr_url = f"https://epes.online/pes/{self.id}/"

                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(qr_url)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")
                canvas = BytesIO()
                img.save(canvas, format='PNG')
                canvas.seek(0)

                fname = f'qr_pes_{self.id}.png'
                self.qr_kod.save(fname, File(canvas), save=False)

                # Uložíme pouze pole qr_kod, abychom nezacyklili save()
                super().save(update_fields=['qr_kod'])
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
    # on_delete=models.CASCADE zajistí, že při smazání psa zmizí i jeho galerie
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

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nazev)
        super().save(*args, **kwargs)


class Prispevek(models.Model):
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    # Necháme null=True, aby zeď fungovala i pro služby bez plemene
    plemeno = models.ForeignKey(Plemeno, on_delete=models.CASCADE, related_name='prispevky_na_zed', null=True, blank=True)
    # TOTO JE KLÍČOVÉ POLE:
    sekce_slug = models.CharField(max_length=100, db_index=True, blank=True)
    text = models.TextField()
    obrazek = models.ImageField(upload_to='prispevky/', blank=True, null=True)
    video = models.FileField(upload_to='videa/', blank=True, null=True)
    datum_pridani = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='libi_se_mi', blank=True)


class Komentar(models.Model):
    prispevek = models.ForeignKey(Prispevek, on_delete=models.CASCADE, related_name='komentare')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    datum_pridani = models.DateTimeField(auto_now_add=True)


class Notifikace(models.Model):
    prijemce = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prijate_notifikace')
    odesilatel = models.ForeignKey(User, on_delete=models.CASCADE)
    typ = models.CharField(max_length=20)  # 'like', 'komentar'
    prispevek = models.ForeignKey(Prispevek, on_delete=models.CASCADE, null=True)
    precteno = models.BooleanField(default=False)
    datum_vytvoreni = models.DateTimeField(auto_now_add=True)