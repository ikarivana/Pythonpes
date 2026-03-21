import os
import json
import io
from datetime import timedelta, timezone, date

from PIL import Image, ImageOps
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models.functions import datetime
from pillow_heif import register_heif_opener

from django.conf import settings
from django.contrib.auth import login
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
import qrcode
from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.core.files.base import ContentFile
from .forms import UserUpdateForm, PlemenoForm, PrispevekForm, ExtendedRegistrationForm, OckovaniForm, PesForm, \
    ProfilUpdateForm
from .models import Plemeno, Prispevek, Komentar, GalerieFotka, GalerieVideo, Uspech, Pes, \
    ZdravotniZaznam, Notifikace, Like, ProfilMajitele, PromoKod

# Ostatní nástroje
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# Aktivace podpory HEIC (iPhone fotky)
register_heif_opener()


def zpracuj_foto(input_file):
    # Otevřeme obrázek (Pillow díky openeru zvládne i HEIC)
    img = Image.open(input_file)

    # Převedeme na RGB (odstraní průhlednost u PNG a HEIC)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Zmenšíme fotku, pokud je moc velká (max 1200px šířka)
    max_size = (1200, 1200)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Uložíme do paměti jako JPEG
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85)  # Kvalita 85 je ideální kompromis
    output.seek(0)

    return ContentFile(output.read(), name=input_file.name.rsplit('.', 1)[0] + '.jpg')


@login_required
def dashboard(request):
    # 1. Získáme profil (get_or_create je jistota, aby to nespadlo)
    profil, _ = ProfilMajitele.objects.get_or_create(uzivatel=request.user)

    # 2. Kontrola, zda premium neprošlo (pokud používáš premium_do)
    # K tomu potřebuješ: from datetime import date
    if profil.is_premium and profil.premium_do:
        if profil.premium_do < date.today():
            profil.is_premium = False
            profil.save()
            messages.warning(request, "Vaše Premium období právě vypršelo.")

    # 3. Načtení dat pro uživatele
    psi = Pes.objects.filter(majitel=profil)

    # Statistiky (kolik má čeho)
    pocet_psu = psi.filter(druh='pes').count()
    pocet_kocek = psi.filter(druh='kocka').count()

    # Poslední zdravotní záznamy pro všechna jeho zvířata
    posledni_zaznamy = ZdravotniZaznam.objects.filter(pes__majitel=profil).order_by('-datum')[:5]

    # Notifikace (nepřečtené)
    nots = request.user.prijate_notifikace.filter(precteno=False).order_by('-datum_vytvoreni')

    context = {
        'profil': profil,
        'psi': psi,
        'pocet_psu': pocet_psu,
        'pocet_kocek': pocet_kocek,
        'posledni_zaznamy': posledni_zaznamy,
        'nots': nots,
        # Pomocná proměnná pro šablonu, aby věděla, jestli zbývá málo dní premia
        'premium_konci_brzy': False
    }

    # Bonus: Varování, pokud premium končí za méně než 3 dny
    if profil.is_premium and profil.premium_do:
        rozdil = (profil.premium_do - date.today()).days
        if 0 <= rozdil <= 3:
            context['premium_konci_brzy'] = True

    return render(request, 'users/dashboard.html', context)


# --- 1. SPRÁVA PSŮ (Základní operace) ---

@login_required
def seznam_psu(request):
    # 1. Získáme nebo vytvoříme profil
    profil, created = ProfilMajitele.objects.get_or_create(uzivatel=request.user)

    # 2. Načteme všechna zvířata daného majitele
    psi = Pes.objects.filter(majitel=profil)

    # 3. LOGIKA LIMITŮ A STATISTIKY
    pocet_psu = psi.filter(druh='pes').count()
    pocet_kocek = psi.filter(druh='kocka').count()

    # Sečteme fotky a videa
    pocet_fotek = GalerieFotka.objects.filter(pes__majitel=profil).count()
    pocet_videi = GalerieVideo.objects.filter(pes__majitel=profil).count()

    # 4. NOTIFIKACE A DATUMY
    # Předpokládám, že related_name v modelu Notifikace je 'prijate_notifikace'
    try:
        nots = request.user.prijate_notifikace.filter(precteno=False).order_by('-datum_vytvoreni')
    except AttributeError:
        nots = []  # Pokud notifikace ještě nemáš nastavené

    dnes_plus_3 = timezone.now().date() + timedelta(days=3)

    # 5. JEDEN FINÁLNÍ RETURN
    # Tady používám 'users/seznam_psu.html', protože tak se jmenuje tvoje šablona s kartami
    return render(request, 'users/seznam_psu.html', {
        'psi': psi,
        'nots': nots,
        'profil': profil,
        'dnes_plus_3': dnes_plus_3,
        'pocet_psu': pocet_psu,
        'pocet_kocek': pocet_kocek,
        'pocet_fotek': pocet_fotek,
        'pocet_videi': pocet_videi,
    })


@login_required
def pridat_psa(request):
    profil = get_object_or_404(ProfilMajitele, uzivatel=request.user)

    # Načteme počty pro kontrolu limitů
    pocet_psu = profil.psi.filter(druh='pes').count()
    pocet_kocek = profil.psi.filter(druh='kocka').count()

    if request.method == 'POST':
        form = PesForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            # 1. KONTROLA LIMITŮ PŘED ULOŽENÍM
            if not profil.is_premium and not request.user.is_staff:
                novy_druh = form.cleaned_data.get('druh')

                if novy_druh == 'pes' and pocet_psu >= 1:
                    messages.warning(request, "Ve verzi Free můžete mít pouze jednoho pejska.")
                    return redirect('profil_uzivatele')

                if novy_druh == 'kocka' and pocet_kocek >= 1:
                    messages.warning(request, "Ve verzi Free můžete mít pouze jednu kočičku.")
                    return redirect('profil_uzivatele')

            try:
                pes = form.save(commit=False)
                pes.majitel = profil

                if 'fotka' in request.FILES:
                    pes.fotka = zpracuj_foto(request.FILES['fotka'])

                for pole in ['otec_manualni', 'matka_manualni', 'zdravotni_testy', 'bonitace', 'typ_ochrany_klistata']:
                    if hasattr(pes, pole) and not getattr(pes, pole):
                        setattr(pes, pole, "Nezadáno")

                pes.save()

                # QR Generování
                url_psa = f"https://epes.online/users/pes/{pes.id}/"
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(url_psa)
                qr.make(fit=True)
                img_qr = qr.make_image(fill_color="black", back_color="white")
                buffer = io.BytesIO()
                img_qr.save(buffer, format='PNG')
                filename = f'qr_{pes.id}_{slugify(pes.jmeno)}.png'
                pes.qr_kod.save(filename, ContentFile(buffer.getvalue()), save=True)

                messages.success(request, f"{pes.jmeno} byl/a úspěšně přidán/a!")
                return redirect('seznam_psu')

            except Exception as e:
                messages.error(request, f"Kritická chyba: {e}")
        else:
            # Tento blok patří k "if form.is_valid():"
            print(f"CHYBY FORMULÁŘE: {form.errors}")
            messages.error(request, "Formulář obsahuje chyby.")

    else:
        # 2. PREVENTIVNÍ KONTROLA PŘI VSTUPU (GET)
        if not profil.is_premium and not request.user.is_staff:
            if pocet_psu >= 1 and pocet_kocek >= 1:
                messages.info(request, "Dosáhli jste limitu Free verze (1 pes + 1 kočka).")
                return redirect('profil_uzivatele')

        form = PesForm(request=request)

    return render(request, 'users/pridat_psa.html', {'form': form})


@login_required
def upravit_psa(request, pk):
    profil, _ = ProfilMajitele.objects.get_or_create(uzivatel=request.user)
    pes = get_object_or_404(Pes, pk=pk, majitel=profil)

    if request.method == 'POST':
        form = PesForm(request.POST, request.FILES, instance=pes, request=request)
        if form.is_valid():
            try:
                # 1. Uložíme základ z formuláře, ale ještě ne do DB
                pes = form.save(commit=False)

                # 2. MANUÁLNÍ PŘIŘAZENÍ (to co formulář nepokryl)
                pes.rasa = request.POST.get('rasa')
                # Ošetření prázdného datumu, aby nepadala DB
                datum_nar = request.POST.get('datum_narozeni')
                pes.datum_narozeni = datum_nar if datum_nar else None

                pes.otec_manualni = request.POST.get('otec') or "Nezadáno"
                pes.matka_manualni = request.POST.get('matka') or "Nezadáno"
                pes.kontaktni_telefon = request.POST.get('kontaktni_telefon')
                pes.popis = request.POST.get('popis')

                # Prevence
                pes.posledni_ockovani = request.POST.get('posledni_ockovani') or None
                pes.posledni_odcerveni = request.POST.get('posledni_odcerveni') or None
                pes.posledni_klistata = request.POST.get('posledni_klistata') or None

                # 3. FINÁLNÍ ULOŽENÍ
                pes.save()

                messages.success(request, "Změny byly úspěšně uloženy!")
                # Pozor: název URL musí odpovídat tvému urls.py (pravděpodobně 'detail_psa')
                return redirect('detail_psa', pes.id)

            except Exception as e:
                messages.error(request, f"Chyba při ukládání: {e}")
        else:
            print(form.errors)  # Tohle uvidíš v terminálu, pokud to selže
            messages.error(request, "Formulář obsahuje chyby.")
    else:
        form = PesForm(instance=pes, request=request)

    return render(request, 'users/upravit_psa.html', {  # Cesta k šabloně, kterou jsme ladili
        'pes': pes,
        'form': form,
        'je_majitel': True
    })


def detail_psa(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id)
    # Získání záznamů z deníku (tohle ti tam chybělo!)
    zdravotni_zaznamy = pes.denik.all().order_by('-datum')

    galeriefotky = GalerieFotka.objects.filter(pes=pes)
    galerievidea = GalerieVideo.objects.filter(pes=pes)
    uspechy = pes.uspechy.all().order_by('-datum')
    potomci = pes.potomci.all().order_by('-datum_narozeni')

    je_majitel = False
    je_premium = pes.je_premium

    if request.user.is_authenticated:
        if pes.majitel and pes.majitel.uzivatel == request.user:
            je_majitel = True
        if request.user.is_superuser:
            je_premium = True

    return render(request, 'users/detail_psa.html', {  # Ujisti se, že se soubor jmenuje takto
        'pes': pes,
        'je_majitel': je_majitel,
        'je_premium': je_premium,
        'zdravotni_zaznamy': zdravotni_zaznamy,
        'galeriefotky': galeriefotky,
        'galerievidea': galerievidea,
        'uspechy': uspechy,
        'potomci': potomci,
        'today': timezone.now().date(),
    })

@login_required
def smazat_psa(request, pk):
    # Najdeme psa, který patří přihlášenému uživateli
    pes = get_object_or_404(Pes, pk=pk, majitel=request.user.profil)

    if request.method == 'POST':
        jmeno_psa = pes.jmeno
        pes.delete()
        messages.success(request, f"Pejsek {jmeno_psa} byl úspěšně smazán.")
        return redirect('profil')

    return render(request, 'users/smazat_psa_potvrzeni.html', {'pes': pes})


# --- 2. MULTIMÉDIA (Galerie - Nahrávání a mazání) ---
@login_required
def pridat_foto(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id, majitel__uzivatel=request.user)

    if request.method == 'POST':
        file = request.FILES.get('obrazek')
        if file:
            filename = file.name.lower()

            try:
                # Otevřeme obrázek (Pillow díky register_heif_opener zvládne i HEIC)
                image = Image.open(file)

                # --- OPRAVA ROTACE (EXIF) ---
                # Toto zajistí, že fotka nebude na bok, pokud ji tak iPhone vyfotil
                image = ImageOps.exif_transpose(image)

                # Pokud je to HEIC nebo chceme vynutit JPG pro všechno (doporučeno)
                if filename.endswith('.heic') or filename.endswith('.heif') or True:
                    # Převedeme na RGB (nutné pro JPG)
                    if image.mode in ("RGBA", "P"):
                        image = image.convert('RGB')
                    else:
                        image = image.convert('RGB')

                    # Uložíme do paměti jako JPG
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=85, optimize=True)

                    # Vytvoříme nový název souboru
                    new_filename = filename.rsplit('.', 1)[0] + ".jpg"
                    file = ContentFile(buffer.getvalue(), name=new_filename)

                # Uložení do databáze
                GalerieFotka.objects.create(pes=pes, obrazek=file)
                messages.success(request, "Fotka byla úspěšně nahrána.")

            except Exception as e:
                messages.error(request, f"Chyba při zpracování obrázku: {e}")

    return redirect('detail_psa', pes_id=pes_id)


@login_required
def smazat_foto(request, pk):
    # Najdeme fotku a ověříme majitele
    foto = get_object_or_404(GalerieFotka, id=pk, pes__majitel__uzivatel=request.user)
    pes_id = foto.pes.id
    foto.delete()
    messages.success(request, "Fotka byla úspěšně smazána.")
    # VRACÍME SE NA DETAIL - parametr musí být pes_id (podle tvého urls.py)
    return redirect('detail_psa', pes_id=pes_id)


@login_required
def pridat_video(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id, majitel__uzivatel=request.user)
    if request.method == 'POST':
        vid = request.FILES.get('video_soubor') # Musí sedět s name="video_soubor" v HTML
        if vid:
            # TADY: musí být video_soubor=vid (podle vašeho modelu)
            GalerieVideo.objects.create(pes=pes, video_soubor=vid)
            messages.success(request, "Video nahráno.")
        else:
            messages.error(request, "Soubor nebyl vybrán.")
    return redirect('detail_psa', pes_id=pes.id)

@login_required
def smazat_video(request, pk):
    video = get_object_or_404(GalerieVideo, id=pk, pes__majitel__uzivatel=request.user)
    p_id = video.pes.id
    video.delete()
    messages.success(request, "Video smazáno.")
    return redirect('detail_psa', pes_id=p_id)


def nouzovy_profil_psa(request, pes_id):
    # Tady by měla být logika pro zobrazení nouzového profilu
    # (pokud pes není ztracený, přesměrovat na normální detail, atd.)
    pes = get_object_or_404(Pes, id=pes_id)

    context = {
        'pes': pes,
        'nouzovy_rezim': pes.je_ztraceny,
    }
    return render(request, 'users/nouzovy_profil.html', context)


def odeslat_sos_email(request, pes_id):
    if request.method == 'POST':
        pes = get_object_or_404(Pes, id=pes_id)
        zprava_od_nalezce = request.POST.get('zprava')
        kontakt_nalezce = request.POST.get('kontakt', 'Neuveden')

        # Nové: Kontrola, zda nálezce klikl na "Pejsek je u mě v bezpečí"
        nalezene_potvrzeno = request.POST.get('pes_v_bezpeci') == 'on'

        if nalezene_potvrzeno:
            pes.je_ztraceny = False  # Automaticky vypneme režim ztráty
            pes.save()
            status_text = "PEJSEK JE V BEZPEČÍ U NÁLEZCE"
        else:
            status_text = "Zpráva od nálezce"

        obsah = (
            f"Dobrý den,\n\n{status_text} u vašeho psa {pes.jmeno}.\n\n"
            f"ZPRÁVA: {zprava_od_nalezce}\n"
            f"KONTAKT NA NÁLEZCE: {kontakt_nalezce}\n\n"
            f"Tato zpráva byla odeslána automaticky z portálu e-pes.cz."
        )

        send_mail(
            f"🐾 {status_text}: {pes.jmeno}",
            obsah,
            'sos@e-pes.cz',
            [pes.majitel.uzivatel.email],
            fail_silently=False,
        )
        messages.success(request, "Informace byla majiteli odeslána. Děkujeme za pomoc!")

    return redirect('nouzovy_profil_psa', pes_id=pes_id)


def prepnout_ztratu(request, pes_id):
    profil = get_object_or_404(ProfilMajitele, uzivatel=request.user)
    pes = get_object_or_404(Pes, id=pes_id, majitel=profil)

    # Přepneme ANO/NE
    pes.je_ztraceny = not pes.je_ztraceny

    if pes.je_ztraceny:
        # Přečteme lat/lon z URL (to co tam pošle JavaScript)
        lat = request.GET.get('lat')
        lon = request.GET.get('lon')

        if lat and lon and lat != '0' and lat != 'None':
            try:
                pes.lat = float(str(lat).replace(',', '.'))
                pes.lon = float(str(lon).replace(',', '.'))
            except (ValueError, TypeError):
                # Fallback na střed ČR, pokud se převod nepovede
                pes.lat = 49.8175
                pes.lon = 15.4730
        else:
            # Pokud GPS není k dispozici, dáme střed ČR
            pes.lat = 49.8175
            pes.lon = 15.4730
    else:
        # Při nalezení vymažeme polohu z mapy
        pes.lat = None
        pes.lon = None

    pes.save()
    return redirect('detail_psa', pes_id=pes.id)

@csrf_exempt
def odeslat_polohu_nalezu(request, pes_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lat = data.get('lat')
            lng = data.get('lng')
            pes = get_object_or_404(Pes, id=pes_id)

            if pes.je_ztraceny and lat and lng:
                # Správný formát Google Maps odkazu
                map_url = f"https://www.google.com/maps?q={lat},{lng}"

                # Hezčí text e-mailu pro majitele
                predmet = f"🚨 POLOHA NÁLEZU: {pes.jmeno}!"
                zprava = (
                    f"Dobrý den,\n\n"
                    f"máme skvělou zprávu! QR kód vašeho pejska {pes.jmeno} byl právě naskenován.\n\n"
                    f"PŘIBLIŽNÁ POLOHA NÁLEZCE:\n{map_url}\n\n"
                    f"Tato poloha byla zaměřena pomocí GPS telefonu nálezce v momentě naskenování.\n"
                    f"Tým e-pes.cz"
                )

                send_mail(
                    predmet,
                    zprava,
                    'sos@e-pes.cz',  # Ujisti se, že máš tohle nastavené v settings.py
                    [pes.majitel.uzivatel.email],
                    fail_silently=False,
                )
                return JsonResponse({'status': 'email_odeslan'})

            return JsonResponse({'status': 'pes_neni_ztracen_nebo_chybi_gps'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error'}, status=400)

def seznam_hledanych_psu(request):
    # Vyfiltruje pouze psy, kteří jsou označeni jako ztracení
    hledani_psi = Pes.objects.filter(je_ztraceny=True).order_by('-id')
    return render(request, 'users/seznam_hledanych.html', {'psi': hledani_psi})


# --- 4. ZDRAVÍ A PDF ---
@login_required
def veterinar(request):
    profil, _ = ProfilMajitele.objects.get_or_create(uzivatel=request.user)
    vybrany_pes_id = request.GET.get('pes_id')

    if request.method == 'POST':
        pes = get_object_or_404(Pes, id=request.POST.get('pes_id'), majitel=profil)

        # OPRAVA: ZdravotniZaznam() got unexpected keyword arguments: 'popis'
        # V modelu máš 'poznamka', ne 'popis'.
        # OPRAVA: type object 'datetime.timezone' has no attribute 'now'
        ZdravotniZaznam.objects.create(
            pes=pes,
            datum=request.POST.get('datum') or timezone.now().date(),
            titulek=request.POST.get('titulek'),
            poznamka=request.POST.get('popis'),  # Mapujeme 'popis' z HTML na 'poznamka' v DB
            typ=request.POST.get('typ')
        )
        return redirect(f"{request.path}?pes_id={pes.id}")

    zaznamy = ZdravotniZaznam.objects.filter(pes__majitel=profil).order_by('-datum')
    vybrany_pes = None
    if vybrany_pes_id:
        vybrany_pes = get_object_or_404(Pes, id=vybrany_pes_id, majitel=profil)
        zaznamy = zaznamy.filter(pes=vybrany_pes)

    return render(request, 'users/veterinar.html', {
        'psi': profil.psi.all(),
        'posledni_zaznamy': zaznamy,
        'vybrany_pes': vybrany_pes,
        'today': timezone.now().date()
    })


@login_required
def upravit_zaznam(request, pk):
    # Najdeme záznam a ověříme, že patří psovi přihlášeného uživatele
    zaznam = get_object_or_404(ZdravotniZaznam, pk=pk, pes__majitel=request.user.profil)

    if request.method == 'POST':
        zaznam.titulek = request.POST.get('titulek')
        zaznam.popis = request.POST.get('popis')
        zaznam.save()
        messages.success(request, "Zdravotní záznam byl upraven.")
        return redirect('veterinar')

    return render(request, 'users/upravit_zaznam.html', {'zaznam': zaznam})


@login_required
def smazat_zaznam(request, pk):
    zaznam = get_object_or_404(ZdravotniZaznam, pk=pk, pes__majitel=request.user.profil)
    if request.method == 'POST':
        zaznam.delete()
        messages.success(request, "Záznam byl smazán.")
        return redirect('veterinar')
    return render(request, 'users/smazat_zaznam_potvrzeni.html', {'zaznam': zaznam})


# Tato funkce je KLÍČOVÁ pro obrázky v PDF
def link_callback(uri, rel):
    """
    Převádí HTML URI na absolutní cesty k souborům na disku.
    """
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    elif uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    else:
        return uri

    # Zkontrolujeme, zda soubor skutečně existuje
    if not os.path.isfile(path):
        return uri
    return path


@login_required
def export_pes_pdf(request, pes_id):
    # BEZPEČNOST: Kontrola, že pes patří přihlášenému uživateli
    pes = get_object_or_404(Pes, id=pes_id, majitel=request.user.profil)

    # Získání profilu uživatele pro kontrolu is_premium
    profil = request.user.profil

    # Definice cesty k fontu
    font_path = os.path.join(settings.MEDIA_ROOT, 'fonts', 'DejaVuSans.ttf')

    # REGISTRACE: Název 'DejaVu Sans' musí být PŘESNĚ jako v HTML šabloně
    pdfmetrics.registerFont(TTFont('DejaVu Sans', font_path))

    template = get_template('users/pdf_sablona.html')

    # PŘIDÁNO: 'profil': profil
    context = {
        'pes': pes,
        'profil': profil,
        'media_root': settings.MEDIA_ROOT,
    }

    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="export_{pes.jmeno}.pdf"'

    pisa_status = pisa.CreatePDF(
        html,
        dest=response,
        encoding='utf-8',
        link_callback=link_callback
    )

    if pisa_status.err:
        return HttpResponse(f'Chyba při generování PDF: {pisa_status.err}')

    return response

# --- 1. SOCIÁLNÍ SÍŤ - SEZNAM ZDÍ ---
def seznam_zdi(request):
    vsechna_plemena = Plemeno.objects.all().order_by('nazev')
    context = {
        'vsechna_plemena': vsechna_plemena.filter(kategorie='ostatni'),
        'plemena_vystavy': vsechna_plemena.filter(kategorie='vystavy'),
        'plemena_lovecka': vsechna_plemena.filter(kategorie='lovecka'),
    }
    return render(request, 'users/social_zed.html', context)


# --- 2. ZED PŘÍSPĚVKŮ ---
def zed_plemene(request, slug):
    plemeno = get_object_or_404(Plemeno, slug=slug)
    prispevky = Prispevek.objects.filter(plemeno=plemeno) \
        .select_related('autor') \
        .prefetch_related('komentare__autor') \
        .order_by('-datum_pridani')

    form = PrispevekForm()

    # Logika pro POST (přidávání) zůstává chráněna
    if request.method == 'POST':
        # Pokud není přihlášen, nepovolíme mu POST požadavek
        if not request.user.is_authenticated:
            messages.error(request, "Pro přidávání příspěvků se musíte přihlásit.")
            return redirect('login')

        if 'btn_prispevek' in request.POST:
            form = PrispevekForm(request.POST, request.FILES)
            if form.is_valid():
                prispevek = form.save(commit=False)
                prispevek.autor = request.user
                prispevek.plemeno = plemeno
                prispevek.save()
                messages.success(request, "Příspěvek byl publikován.")
                return redirect('zed_plemene', slug=slug)

        elif 'btn_komentar' in request.POST:
            prispevek_id = request.POST.get('prispevek_id')
            prispevek = get_object_or_404(Prispevek, id=prispevek_id)
            text = request.POST.get('text_komentare')
            if text:
                Komentar.objects.create(
                    prispevek=prispevek,
                    autor=request.user,
                    text=text
                )
                return redirect('zed_plemene', slug=slug)

    return render(request, 'users/zed.html', {
        'form': form,
        'plemeno': plemeno,
        'prispevky': prispevky,
        'slug': slug
    })


@login_required
def pridat_odpoved(request, parent_id):
    parent_komentar = get_object_or_404(Komentar, id=parent_id)

    if request.method == 'POST':
        text = request.POST.get('text_odpovedi')
        if text:
            # Vytvoření odpovědi (komentáře, který má rodiče)
            nova_odpoved = Komentar.objects.create(
                prispevek=parent_komentar.prispevek,
                autor=request.user,
                text=text,
                parent=parent_komentar  # Zde je nutné mít pole 'parent' v modelu Komentar
            )

            # Notifikace vlastníkovi rodičovského komentáře
            if parent_komentar.autor != request.user:
                Notifikace.objects.create(
                    prijemce=parent_komentar.autor,
                    odesilatel=request.user,
                    typ='odpoved',
                    komentar=nova_odpoved
                )
            messages.success(request, "Odpověď byla přidána.")

        return redirect('zed_plemene', slug=parent_komentar.prispevek.plemeno.slug)

    return redirect('zed_plemene', slug=parent_komentar.prispevek.plemeno.slug)


@login_required
def upravit_komentar(request, pk):
    komentar = get_object_or_404(Komentar, id=pk)
    # Kontrola, zda je uživatel autorem komentáře
    if komentar.autor == request.user:
        if request.method == 'POST':
            # Logika pro uložení změn (např. pomocí CommentForm)
            text = request.POST.get('text_komentare')
            if text:
                komentar.text = text
                komentar.save()
                messages.success(request, "Komentář byl upraven.")
                return redirect('zed_plemene', slug=komentar.prispevek.plemeno.slug)
        return render(request, 'users/upravit_komentar.html', {'komentar': komentar})
    else:
        messages.error(request, "Nemáte oprávnění.")
        return redirect('zed_plemene', slug=komentar.prispevek.plemeno.slug)


# --- 3. PŘIDÁNÍ POLOŽKY (S KATEGORIÍ) ---
@login_required
def pridat_polozku_vse(request, typ_kategorie):
    if request.method == 'POST':
        form = PlemenoForm(request.POST, request.FILES)
        if form.is_valid():
            plemeno = form.save(commit=False)

            # Nastavení kategorie podle URL (vystavy/lovecka/ostatni)
            plemeno.kategorie = typ_kategorie

            navrzeny_slug = slugify(plemeno.nazev)

            # Kontrola duplicity
            if Plemeno.objects.filter(slug=navrzeny_slug).exists():
                messages.error(request, f"Položka s názvem '{plemeno.nazev}' již existuje!")
                return render(request, 'users/pridat_polozku.html', {'form': form, 'typ': typ_kategorie})

            plemeno.slug = navrzeny_slug
            plemeno.save()
            messages.success(request, f"Položka {plemeno.nazev} byla přidána.")
            return redirect('seznam_zdi')
    else:
        form = PlemenoForm()
    return render(request, 'users/pridat_polozku.html', {'form': form, 'typ': typ_kategorie})


# --- 4. ADMIN TLAČÍTKA (MAZÁNÍ) ---
@staff_member_required
def smazat_plemeno(request, plemeno_id):
    plemeno = get_object_or_404(Plemeno, id=plemeno_id)
    if request.method == 'POST':
        plemeno.delete()
        messages.success(request, "Položka byla smazána.")
    return redirect('seznam_zdi')


# --- 5. ÚPRAVA A MAZÁNÍ PŘÍSPĚVKŮ (OPRÁVNĚNÍ) ---
@login_required
def upravit_prispevek(request, pk):
    prispevek = get_object_or_404(Prispevek, pk=pk, autor=request.user)

    if request.method == 'POST':
        form = PrispevekForm(request.POST, request.FILES, instance=prispevek)
        if form.is_valid():
            form.save()
            messages.success(request, "Příspěvek byl upraven.")
            return redirect('zed_plemene', slug=prispevek.plemeno.slug)
    else:
        form = PrispevekForm(instance=prispevek)

    return render(request, 'users/upravit_prispevek.html', {'form': form, 'prispevek': prispevek})


@login_required
def smazat_prispevek(request, pk):
    # Povolit vlastníkovi nebo adminovi
    if request.user.is_staff:
        prispevek = get_object_or_404(Prispevek, pk=pk)
    else:
        prispevek = get_object_or_404(Prispevek, pk=pk, autor=request.user)

    slug = prispevek.plemeno.slug if prispevek.plemeno else None

    if request.method == 'POST':
        prispevek.delete()
        messages.success(request, "Příspěvek byl smazán.")
        if slug:
            return redirect('zed_plemene', slug=slug)
        else:
            return redirect('seznam_zdi')

    return render(request, 'users/smazat_prispevek_potvrzeni.html', {'prispevek': prispevek})


@login_required
def pridej_like(request, post_id):
    p = get_object_or_404(Prispevek, id=post_id)
    liked = False

    # 1. Kontrola existence lajku v tabulce Like (pro Profil)
    existujici_like = Like.objects.filter(uzivatel=request.user, prispevek=p).first()

    if existujici_like:
        # Pokud existuje, odebíráme (Un-like)
        existujici_like.delete()
        p.likes.remove(request.user)  # Synchronizace ManyToMany pole u příspěvku
        liked = False
    else:
        # Pokud neexistuje, vytváříme (Like)
        Like.objects.get_or_create(uzivatel=request.user, prispevek=p)
        p.likes.add(request.user)  # Synchronizace ManyToMany pole u příspěvku
        liked = True

        # 2. Vytvoření notifikace pro autora (jen pokud si nelajkuje vlastní post)
        if p.autor != request.user:
            Notifikace.objects.create(
                prijemce=p.autor,
                odesilatel=request.user,
                typ='like',
                prispevek=p
            )

    # 3. Odpověď pro AJAX (pro JavaScript na zdi - stránka se neobnoví)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'liked': liked,
            'count': p.likes.count()
        })

    # 4. Klasický redirect pro případ, že JS nefunguje nebo klikáš z profilu
    referer = request.META.get('HTTP_REFERER', '/')
    base_url = referer.split('#')[0]

    return redirect(f"{base_url}#post-{p.id}")


@login_required
def smazat_komentar(request, pk):
    komentar = get_object_or_404(Komentar, id=pk)
    # Povolit vlastníkovi komentáře, autorovi příspěvku nebo adminovi
    if komentar.autor == request.user or komentar.prispevek.autor == request.user or request.user.is_staff:
        slug = komentar.prispevek.plemeno.slug
        komentar.delete()
        messages.success(request, "Komentář byl smazán.")
        return redirect('zed_plemene', slug=slug)
    else:
        messages.error(request, "Nemáte oprávnění.")
        return redirect(request.META.get('HTTP_REFERER', '/'))


# --- REGISTRACE ---
def register(request):
    if request.method == 'POST':
        form = ExtendedRegistrationForm(request.POST)
        if form.is_valid():
            # save() v tvém forms.py už vytvoří uživatele i ProfilMajitele
            user = form.save()

            login(request, user)
            messages.success(request, f"Vítej, {user.first_name}! Registrace proběhla úspěšně.")

            # OPRAVA: Směrujeme na 'name' z urls.py
            return redirect('profil')
    else:
        form = ExtendedRegistrationForm()
    return render(request, 'users/register.html', {'form': form})


# --- PROFIL ---
@login_required
def profil_uzivatele(request):
    # Získání nebo vytvoření profilu
    profil, created = ProfilMajitele.objects.get_or_create(uzivatel=request.user)

    # Statistiky pro šablonu
    lajky = Like.objects.filter(uzivatel=request.user)
    komentare = Komentar.objects.filter(autor=request.user)

    context = {
        'profil': profil,
        'libi_se_mi': lajky,
        'komentare': komentare,
    }
    return render(request, 'users/profil.html', context)


# --- UPRAVIT PROFIL ---
@login_required
def upravit_profil(request):
    profil, created = ProfilMajitele.objects.get_or_create(uzivatel=request.user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profil_form = ProfilUpdateForm(request.POST, request.FILES, instance=profil)

        if user_form.is_valid() and profil_form.is_valid():
            user_form.save()
            profil_form.save()
            messages.success(request, "Profil byl úspěšně upraven.")
            return redirect('profil')  # <--- ZKONTROLUJ, že v urls.py máš name='profil'
    else:
        user_form = UserUpdateForm(instance=request.user)
        profil_form = ProfilUpdateForm(instance=profil)

    context = {
        'user_form': user_form,
        'profil_form': profil_form,
        'profil': profil,
    }
    return render(request, 'users/upravit_profil.html', context)


@login_required
def aktivovat_promokod(request):
    if request.method == 'POST':
        kod_text = request.POST.get('kod', '').strip()
        try:
            # Najdeme kód v databázi
            promo = PromoKod.objects.get(kod=kod_text, je_aktivni=True)

            # Získáme profil uživatele
            profil, _ = ProfilMajitele.objects.get_or_create(uzivatel=request.user)

            # Logika prodloužení: pokud už premium má, přičteme dny k datu konce,
            # jinak přičteme dny k dnešku.
            start_date = profil.premium_do if (profil.premium_do and profil.premium_do > date.today()) else date.today()
            profil.premium_do = start_date + timedelta(days=promo.pocet_dni)
            profil.is_premium = True
            profil.save()

            messages.success(request,
                             f"Skvělé! Promo kód aktivován. Premium máte do {profil.premium_do.strftime('%d.%m.%Y')}.")
            return redirect('dashboard')  # nebo kamkoliv jinam

        except PromoKod.DoesNotExist:
            messages.error(request, "Tento promo kód neexistuje nebo již není platný.")

    return render(request, 'users/aktivovat_kod.html')


# --- SMAZAT PROFIL ---
@login_required
def smazat_profil(request):
    uzivatel = request.user
    logout(request)
    uzivatel.delete()
    messages.warning(request, "Tvůj účet byl smazán.")
    return redirect('home')


@login_required
def seznam_notifikaci(request):
    # 1. Načtení notifikací seřazených od nejnovější (mínus před názvem pole)
    # Používáme select_related, aby se ušetřily dotazy do DB pro odesilatele a příspěvek
    notifikace = Notifikace.objects.filter(prijemce=request.user).select_related('odesilatel', 'prispevek').order_by(
        '-datum_vytvoreni')

    # 2. Označení nepřečtených jako přečtené (pouze těch, co jsou False)
    # Je dobré to udělat PŘED renderováním, nebo hned po načtení
    notifikace.filter(precteno=False).update(precteno=True)

    context = {
        'nots': notifikace,
    }
    return render(request, 'users/notifikace.html', context)


def zdravotni_historie(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id)

    zaznamy = pes.denik.all().order_by('-datum')

    return render(request, 'users/zdravotni_historie.html', {
        'pes': pes,
        'zaznamy': zaznamy,
    })


def pridat_zaznam(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id)

    if request.method == 'POST':
        typ = request.POST.get('typ')
        titulek = request.POST.get('titulek')
        poznamka = request.POST.get('poznamka')
        datum_str = request.POST.get('datum')

        # Ošetření prázdného data
        datum = datum_str if datum_str else timezone.now().date()

        # 1. Vytvoření nového záznamu v deníku
        novy_zaznam = ZdravotniZaznam.objects.create(
            pes=pes,
            datum=datum,
            typ=typ,
            titulek=titulek,
            poznamka=poznamka
        )

        # 2. TIP: Pokud má tvůj model ZdravotniZaznam metodu save(),
        # která aktualizuje pole na modelu Pes, zavolej ji explicitně:
        novy_zaznam.save()

        # Návrat zpět do historie deníku
        return redirect('zdravotni_historie', pes_id=pes.id)

    # Pokud někdo přistoupí přes GET, ukážeme formulář (pokud ho nepoužíváš jen v modalu)
    return render(request, 'users/pridat_zaznam_form.html', {
        'pes': pes,
        'today': timezone.now().date()
    })


def pridat_ockovani(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id)

    if request.method == 'POST':
        form = OckovaniForm(request.POST)
        if form.is_valid():
            ockovani = form.save(commit=False)
            ockovani.pes = pes
            ockovani.save()
            return redirect('detail_psa', pes_id=pes.id)
    else:
        form = OckovaniForm()

    return render(request, 'users/pridat_ockovani.html', {
        'form': form,
        'pes': pes,
        'titul': 'Nové očkování'
    })



def kariera_psa(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id)
    # Načteme všechny úspěchy a seřadíme je od nejnovějších
    uspechy = Uspech.objects.filter(pes=pes).order_by('-datum')
    return render(request, 'users/kariera_psa.html', {
        'pes': pes,
        'uspechy': uspechy
    })


def pridat_uspech(request, pes_id):
    if request.method == 'POST':
        pes = get_object_or_404(Pes, id=pes_id)

        # Musíme vytáhnout 'typ' z POST dat, jinak DB hodí IntegrityError
        typ_zaznamu = request.POST.get('typ')
        nazev_akce = request.POST.get('nazev')
        oceneni_text = request.POST.get('oceneni')
        datum_akce = request.POST.get('datum')
        misto_akce = request.POST.get('misto')

        # Uložení do databáze
        Uspech.objects.create(
            pes=pes,
            typ=typ_zaznamu,  # Klíčové pole!
            nazev=nazev_akce,
            oceneni=oceneni_text,
            datum=datum_akce if datum_akce else None,
            misto=misto_akce
        )
        return redirect('detail_psa', pes_id=pes.id)

    return redirect('detail_psa', pes_id=pes_id)


@login_required
def smazat_uspech(request, uspech_id):
    # Najde úspěch nebo vyhodí chybu 404
    uspech = get_object_or_404(Uspech, id=uspech_id)
    pes_id = uspech.pes.id

    # Bezpečnostní kontrola: Je přihlášený uživatel majitelem psa?
    if uspech.pes.majitel.uzivatel == request.user or request.user.is_superuser:
        uspech.delete()
        # Můžeš přidat i zprávu pro uživatele (vyžaduje import messages)
        # messages.success(request, "Úspěch byl úspěšně odstraněn.")

    # Přesměrování zpět na stránku kariéry
    return redirect('kariera_psa', pes_id=pes_id)


def pridat_vrh(request, pes_id):
    # Najdeme zvíře (matku), u které vrh přidáváme
    zvíře = get_object_or_404(Pes, id=pes_id)

    if request.method == 'POST':
        # Vytvoření záznamu v modelu Vrh podle tvých polí
        Vrh.objects.create(
            rodic=zvíře,
            datum_narozeni=request.POST.get('datum_narozeni'),
            oznaceni_vrhu=request.POST.get('oznaceni_vrhu'),
            pocet_psu=request.POST.get('pocet_samcu', 0),
            pocet_fen=request.POST.get('pocet_samic', 0),
            druhy_rodic=request.POST.get('druhy_rodic'),
            poznamka=request.POST.get('poznamka')
        )
        # Po uložení se vrátíme na úpravu zvířete
        return redirect('upravit_psa', pes_id=zvíře.id)

    return render(request, 'users/pridat_vrh.html', {'zvíře': zvíře})