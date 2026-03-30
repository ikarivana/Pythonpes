import os
import json
import io
from datetime import timedelta, timezone

from PIL import Image, ImageOps
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.urls import reverse
from pillow_heif import register_heif_opener

from django.conf import settings
from django.contrib.auth import login
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
import qrcode
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.core.files.base import ContentFile

from home.models import Recenze
from inzerce.models import Inzerat
from .forms import UserUpdateForm, PlemenoForm, PrispevekForm, ExtendedRegistrationForm, OckovaniForm, PesForm, \
    ProfilUpdateForm
from .models import (
    Plemeno, Prispevek, Komentar, GalerieFotka, GalerieVideo,
    Uspech, Pes, ZdravotniZaznam, Notifikace, Like,
    ProfilMajitele, PromoKod, Vrh, Ockovani
)

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


# --- REGISTRACE ---
def register(request):
    if request.method == 'POST':
        form = ExtendedRegistrationForm(request.POST)
        if form.is_valid():
            # save() vytvoří uživatele i ProfilMajitele
            user = form.save()

            # --- NOVÝ KÓD PRO SOUHLAS ---
            # Pokud v POST datech vidíme zaškrtnutý checkbox 'souhlas_vop'
            if 'souhlas_vop' in request.POST:
                # Získáme profil a uložíme souhlas
                profil, created = ProfilMajitele.objects.get_or_create(uzivatel=user)
                profil.souhlas_podminky = True
                profil.save()
            # ---------------------------

            login(request, user)
            messages.success(request, f"Vítej, {user.first_name}! Registrace proběhla úspěšně.")
            return redirect('profil')
    else:
        form = ExtendedRegistrationForm()
    return render(request, 'users/register.html', {'form': form})


# --- ZOBRAZENÍ PROFILU ---
@login_required
def profil_uzivatele(request):
    profil, created = ProfilMajitele.objects.get_or_create(uzivatel=request.user)

    lajky = Like.objects.filter(uzivatel=request.user)
    komentare = Komentar.objects.filter(autor=request.user)

    context = {
        'profil': profil,
        'libi_se_mi': lajky,
        'komentare': komentare,
    }
    return render(request, 'users/profil.html', context)


# --- ÚPRAVA PROFILU (To, co jsme teď tvořili) ---
@login_required
def upravit_profil(request):
    # Získáme profil (pokud neexistuje, vytvoříme ho)
    profil, created = ProfilMajitele.objects.get_or_create(uzivatel=request.user)

    if request.method == 'POST':
        # Pro UserUpdateForm (first_name, last_name, email)
        user_form = UserUpdateForm(request.POST, instance=request.user)
        # Pro ProfilUpdateForm (fotka, telefon, adresa)
        # request.FILES je klíčový pro nahrávání fotky!
        profil_form = ProfilUpdateForm(request.POST, request.FILES, instance=profil)

        if user_form.is_valid() and profil_form.is_valid():
            user_form.save()
            profil_form.save()  # Zde se spustí to automatické otočení fotky z models.py
            messages.success(request, 'Tvůj profil byl úspěšně aktualizován!')
            return redirect('profil')  # Název tvého URL pro zobrazení profilu
    else:
        user_form = UserUpdateForm(instance=request.user)
        profil_form = ProfilUpdateForm(instance=profil)

    context = {
        'user_form': user_form,
        'profil_form': profil_form,
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


from datetime import date # Nezapomeň na importy nahoře

@login_required
def dashboard(request):
    # 1. Získáme profil (get_or_create je jistota)
    profil, _ = ProfilMajitele.objects.get_or_create(uzivatel=request.user)

    # --- PRÁVNÍ STOPKA (VOP) ---
    # Pokud uživatel ještě nesouhlasil s VOP, nepustíme ho dál a hodíme ho na stránku s tlačítkem
    if not profil.souhlas_podminky:
        messages.info(request, "Před pokračováním prosím potvrďte naše aktualizované obchodní podmínky.")
        return redirect('podminky') # 'podminky' je name z urls.py pro tvou stránku s VOP
    # ---------------------------

    # 2. Kontrola expirace Premia
    if profil.is_premium and profil.premium_do:
        if profil.premium_do < date.today():
            profil.is_premium = False
            profil.save()
            messages.warning(request, "Vaše Premium období právě vypršelo.")

    # 3. Načtení dat pro uživatele
    psi = Pes.objects.filter(majitel=profil)

    # Statistiky
    pocet_psu = psi.filter(druh='pes').count()
    pocet_kocek = psi.filter(druh='kocka').count()

    # Poslední zdravotní záznamy
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
            if pocet_psu >= 1 or pocet_kocek >= 1:  # Stačí dosáhnout jednoho z limitů
                messages.info(request, "Ve verzi Free můžete mít pouze jedno zvíře od každého druhu.")
                return redirect('profil_uzivatele')

        form = PesForm(request=request)

    return render(request, 'users/pridat_psa.html', {'form': form})


@login_required
def upravit_psa(request, pk):
    profil = get_object_or_404(ProfilMajitele, uzivatel=request.user)
    pes = get_object_or_404(Pes, pk=pk, majitel=profil)
    byl_ztraceny_predtim = pes.je_ztraceny

    if request.method == 'POST':
        # --- RYCHLÉ SOS PŘES JAVASCRIPT (FETCH) ---
        # Kontrolujeme, zda požadavek obsahuje hlavičku z našeho skriptu
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            lat = request.POST.get('lat')
            lon = request.POST.get('lon')

            if lat and lon:
                pes.lat = float(lat)
                pes.lon = float(lon)
                pes.je_ztraceny = True  # Při SOS automaticky zapneme ztrátu
                pes.save()

                # Vytvoření špendlíku na mapě (stejná logika jako dole)
                from home.models import Sluzba
                Sluzba.objects.update_or_create(
                    vlastnik=request.user,
                    nazev=f"🚨 ZTRACENÝ PES: {pes.jmeno}",
                    defaults={
                        'typ': 'ztrata',
                        'lat': pes.lat,
                        'lon': pes.lon,
                        'adresa': "Poslední známá poloha (GPS)",
                        'telefon': pes.kontaktni_telefon or "",
                        'popis': f"Hledá se {pes.rasa} jménem {pes.jmeno}.",
                        'schvaleno': True
                    }
                )
                return JsonResponse({'status': 'success'})

        # --- KLASICKÉ ULOŽENÍ PŘES FORMULÁŘ ---
        form = PesForm(request.POST, request.FILES, instance=pes, request=request)
        if form.is_valid():
            try:
                pes = form.save()
                from home.models import Sluzba

                if pes.je_ztraceny:
                    Sluzba.objects.update_or_create(
                        vlastnik=request.user,
                        nazev=f"🚨 ZTRACENÝ PES: {pes.jmeno}",
                        defaults={
                            'typ': 'ztrata',
                            'lat': pes.lat,
                            'lon': pes.lon,
                            'adresa': pes.adresa_pro_darky or "Poslední známá poloha",
                            'telefon': pes.kontaktni_telefon or "",
                            'popis': f"Hledá se {pes.rasa} jménem {pes.jmeno}. {pes.popis[:200] if pes.popis else ''}",
                            'schvaleno': True
                        }
                    )
                elif not pes.je_ztraceny and byl_ztraceny_predtim:
                    Sluzba.objects.filter(vlastnik=request.user, nazev__icontains=pes.jmeno, typ='ztrata').delete()

                messages.success(request, f"Změny u zvířete {pes.jmeno} uloženy.")
                return redirect('detail_psa', pes.id)
            except Exception as e:
                messages.error(request, f"Chyba: {e}")
        else:
            messages.error(request, "Opravte chyby ve formuláři.")
    else:
        form = PesForm(instance=pes, request=request)

    return render(request, 'users/upravit_psa.html', {'pes': pes, 'form': form, 'je_majitel': True})

def detail_psa(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id)

    # --- 1. LOGIKA PRO NÁLEZCE (SOS Přesměrování) ---
    # Pokud je pes ztracený a uživatel NENÍ majitel, pošleme ho rovnou na nouzový profil
    je_majitel = False
    if request.user.is_authenticated:
        if pes.majitel and pes.majitel.uzivatel == request.user:
            je_majitel = True

    if pes.je_ztraceny and not je_majitel:
        return redirect('nouzovy_profil_psa', pes_id=pes.id)

    # --- 2. SBĚR DAT PRO PROFIL ---
    zdravotni_zaznamy = pes.denik.all().order_by('-datum')
    galeriefotky = GalerieFotka.objects.filter(pes=pes)
    galerievidea = GalerieVideo.objects.filter(pes=pes)
    uspechy = pes.uspechy.all().order_by('-datum')
    potomci = pes.potomci.all().order_by('-datum_narozeni')

    # --- 3. PREMIUM KONTROLA ---
    # Získáme profil přihlášeného uživatele pro kontrolu is_premium v šabloně
    profil = None
    je_premium = pes.je_premium  # Základní stav ze zvířete

    if request.user.is_authenticated:
        profil = getattr(request.user, 'profil', None)
        if profil and profil.is_premium:
            je_premium = True
        if request.user.is_superuser:
            je_premium = True

    return render(request, 'users/detail_psa.html', {
        'pes': pes,
        'profil': profil,
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


def seznam_hledanych_psu(request):
    ztraceni_psi = Pes.objects.filter(je_ztraceny=True)

    mapa_data = []
    for p in ztraceni_psi:
        if p.lat and p.lon:
            try:
                mapa_data.append({
                    'id': p.id,
                    'nazev': f"🚨 HLEDÁ SE: {p.jmeno}",
                    'lat': float(str(p.lat).replace(',', '.')),
                    'lon': float(str(p.lon).replace(',', '.')),
                    'typ_slug': 'ztrata',
                    'typ': 'ZTRÁTA',
                    'adresa': getattr(p, 'posledni_vyskyt', 'Poloha neupřesněna'),
                    # OPRAVA: reverse automaticky najde správnou cestu podle jména v urls.py
                    'url': reverse('detail_psa', args=[p.id])
                })
            except (ValueError, TypeError):
                continue

    return render(request, 'users/seznam_hledanych.html', {
        'sluzby_json': json.dumps(mapa_data),
        'psi': ztraceni_psi
    })

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
        vid = request.FILES.get('video')
        if vid:
            # Seznam povolených koncovek
            povolene_koncovky = ['.mp4', '.mov', '.webm', '.avi']
            extension = os.path.splitext(vid.name)[1].lower()

            if extension in povolene_koncovky:
                GalerieVideo.objects.create(pes=pes, video_soubor=vid)
                messages.success(request, f"Video ({extension}) bylo úspěšně nahráno.")
            else:
                messages.error(request, f"Formát {extension} není podporován.")
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
    pes = get_object_or_404(Pes, id=pes_id)

    # POJISTKA: Pokud pes NENÍ ztracený, pošleme uživatele na standardní profil.
    # Protože v detail_psa je kontrola (if pes.je_ztraceny),
    # tak nás to SEM už nepustí a smyčka se přeruší.
    if not pes.je_ztraceny:
        return redirect('detail_psa', pes_id=pes.id)

    context = {
        'pes': pes,
        'nouzovy_rezim': True,
        'je_majitel': request.user.is_authenticated and pes.majitel and pes.majitel.uzivatel == request.user
    }
    return render(request, 'users/nouzovy_profil.html', context)


def odeslat_polohu_nalezu(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id)

    if request.method == 'POST':
        lat = request.POST.get('lat')
        lon = request.POST.get('lon')

        if lat and lon:
            # 1. Vytvoříme odkaz na Google Mapy pro majitele
            mapy_link = f"https://www.google.com/maps?q={lat},{lon}"

            # 2. Sestavíme e-mail pro majitele
            subject = f"🚨 NĚKDO NAŠEL VAŠEHO PSA: {pes.jmeno}!"
            message = (
                f"Dobrý den,\n\n"
                f"Někdo právě nahlásil polohu vašeho psa ({pes.jmeno}) přes ePes.online.\n"
                f"Aktuální poloha nálezce: {mapy_link}\n\n"
                f"Prosíme, jednejte rychle!"
            )

            # 3. ODEŠLEME EMAIL (i když nálezce není přihlášen)
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [pes.vlastnik.email],  # E-mail majitele psa
                fail_silently=False,
            )

            return JsonResponse({'status': 'ok', 'message': 'Poloha byla odeslána majiteli.'})

    return JsonResponse({'status': 'error'}, status=400)


def prepnout_ztratu(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id)

    # 1. Přepnutí stavu
    pes.je_ztraceny = not pes.je_ztraceny

    if pes.je_ztraceny:
        # LOGIKA PRO ZAPNUTÍ ZTRÁTY
        lat = request.GET.get('lat')
        lon = request.GET.get('lon')
        if lat and lon:
            try:
                pes.lat = float(lat)
                pes.lon = float(lon)
            except ValueError:
                pass

        # AUTOMATICKY VYTVOŘIT ŠPENDLÍK V MAPĚ SLUŽEB
        # update_or_create zajistí, že nevznikne duplicita pro jednoho psa
        from home.models import Sluzba  # Importuj model Sluzba
        Sluzba.objects.update_or_create(
            nazev=f"🚨 ZTRACENÝ PES: {pes.jmeno}",
            vlastnik=request.user,
            defaults={
                'lat': pes.lat,
                'lon': pes.lon,
                'typ': 'ztrata',
                'schvaleno': True,  # Rovnou schváleno, aby se nemuselo do adminu
                'adresa': "Poslední známá poloha"
            }
        )
    else:
        # LOGIKA PRO VYPNUTÍ ZTRÁTY (Pes se našel)
        # Automaticky smažeme špendlík z mapy služeb
        from home.models import Sluzba
        Sluzba.objects.filter(
            vlastnik=request.user,
            nazev__icontains=pes.jmeno,
            typ='ztrata'
        ).delete()

        # Resetujeme SOS stavy u psa
        pes.je_u_nalezece = False

    pes.save()
    return redirect('detail_psa', pes.id)

@csrf_exempt
def odeslat_polohu_nalezu(request, pes_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pes = get_object_or_404(Pes, id=pes_id)

            pes.lat = data.get('lat')
            pes.lon = data.get('lon')
            pes.je_u_nalezece = True
            pes.save()

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'only POST allowed'}, status=405)


import logging

logger = logging.getLogger(__name__)


@csrf_exempt
def odeslat_sos_email(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id)

    if request.method == 'POST':
        # OPRAVA: Musíme jít přes 'uzivatel', protože tam je uložen e-mail
        try:
            prijemce_email = pes.majitel.uzivatel.email
        except AttributeError:
            # Pojistka, kdyby náhodou majitel neměl uživatele (nemělo by se stát)
            return JsonResponse({'status': 'error', 'message': 'Majitel nemá nastavený e-mail.'})

        lat = request.POST.get('lat', 'Neznámá')
        lon = request.POST.get('lon', 'Neznámá')

        subject = f"🚨 NALEZEN PES: {pes.jmeno}"

        # Vytvoření odkazu na Google Mapy pro majitele
        map_link = f"https://www.google.com/maps?q={lat},{lon}"

        message = (
            f"Dobrý den,\n\n"
            f"někdo právě nahlásil polohu vašeho psa ({pes.jmeno}) přes SOS profil.\n"
            f"Zvíře by mělo být u nálezce v bezpečí.\n\n"
            f"📍 Lokalita na mapě: {map_link}\n"
            f"Zeměpisná šířka: {lat}\n"
            f"Zeměpisná délka: {lon}\n\n"
            f"Tento e-mail byl vygenerován automaticky systémem epes.online."
        )

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [prijemce_email],
                fail_silently=False,
            )
            # Důležité: Vrátit status 'ok', aby JavaScript mohl napsat "Poloha odeslána"
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            # Pokud se něco pokazí (třeba špatné heslo k SMTP), uvidíš to v logu
            print(f"DEBUG CHYBA MAILU: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Chyba při odesílání e-mailu.'})

    return JsonResponse({'status': 'error', 'message': 'Neplatná metoda.'})

def veterinar(request, pes_id=None):
    # 1. Identifikace psa a profilu
    vybrany_pes = None
    profil = None

    if pes_id:
        vybrany_pes = get_object_or_404(Pes, id=pes_id)
        profil = vybrany_pes.majitel
    elif request.user.is_authenticated:
        profil, _ = ProfilMajitele.objects.get_or_create(uzivatel=request.user)
    else:
        return redirect('home')

    # 2. Zpracování POSTu (Ukládání nového záznamu)
    if request.method == 'POST' and request.user.is_authenticated:
        if profil.uzivatel == request.user:
            target_pes_id = request.POST.get('pes_id')
            pes_obj = get_object_or_404(Pes, id=target_pes_id, majitel=profil)

            # Vytvoření záznamu s novým polem 'klinika'
            ZdravotniZaznam.objects.create(
                pes=pes_obj,
                datum=request.POST.get('datum') or timezone.now().date(),
                titulek=request.POST.get('titulek'),
                poznamka=request.POST.get('popis'), # Mapujeme 'popis' z HTML na 'poznamka' v modelu
                typ=request.POST.get('typ'),
                klinika=request.POST.get('klinika') # <--- Nové pole z formu
            )
            return redirect('veterinar', pes_id=pes_obj.id)

    # 3. Logika pro zobrazení
    if vybrany_pes:
        zaznamy_list = ZdravotniZaznam.objects.filter(pes=vybrany_pes).order_by('-datum', '-id')
        vsechny_moje_zaznamy = [vybrany_pes]
    else:
        zaznamy_list = ZdravotniZaznam.objects.filter(pes__majitel=profil).order_by('-datum', '-id')
        vsechny_moje_zaznamy = profil.psi.all()

    # --- STRÁNKOVÁNÍ ---
    paginator = Paginator(zaznamy_list, 6)
    page_number = request.GET.get('page')
    posledni_zaznamy = paginator.get_page(page_number)

    return render(request, 'users/veterinar.html', {
        'psi': vsechny_moje_zaznamy,
        'posledni_zaznamy': posledni_zaznamy,
        'vybrany_pes': vybrany_pes,
        'today': timezone.now().date(),
        # Pomocná proměnná pro modal (aby věděl, ke kterému psovi defaultně ukládat)
        'pes': vybrany_pes or (vsechny_moje_zaznamy[0] if vsechny_moje_zaznamy else None)
    })


@login_required
def upravit_zaznam(request, pk):
    # 1. Bezpečnostní pojistka: Získáme profil a ověříme, že záznam patří přihlášenému uživateli
    profil = get_object_or_404(ProfilMajitele, uzivatel=request.user)
    zaznam = get_object_or_404(ZdravotniZaznam, pk=pk, pes__majitel=profil)

    if request.method == 'POST':
        # 2. Načtení všech dat z tvého nového formuláře
        zaznam.datum = request.POST.get('datum')
        zaznam.titulek = request.POST.get('titulek')
        zaznam.klinika = request.POST.get('klinika')
        zaznam.poznamka = request.POST.get('popis')  # V šabloně máš name="popis"

        # 3. Získání typu s pojistkou proti IntegrityError
        novy_typ = request.POST.get('typ')
        zaznam.typ = novy_typ if novy_typ else 'zaznam'

        zaznam.save()  # Teď už to projde bez NOT NULL chyby

        messages.success(request, "Zdravotní záznam byl úspěšně upraven.")
        return redirect('veterinar', pes_id=zaznam.pes.id)

    # 4. Pro GET požadavek prostě zobrazíme editační stránku
    return render(request, 'users/upravit_zaznam.html', {'zaznam': zaznam})


@login_required
def smazat_zaznam(request, pk):
    profil = get_object_or_404(ProfilMajitele, uzivatel=request.user)
    zaznam = get_object_or_404(ZdravotniZaznam, pk=pk, pes__majitel=profil)

    # Uložíme si ID psa před smazáním pro redirect
    pes_id = zaznam.pes.id

    if request.method == 'POST':
        zaznam.delete()
        messages.success(request, "Záznam byl smazán.")
        return redirect('veterinar', pes_id=pes_id)

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
    # Načteme psa (kontrola majitele je v pořádku)
    pes = get_object_or_404(Pes, id=pes_id, majitel=request.user.profil)

    # Použijeme přímý filtr, abychom se vyhnuli chybám s '_set'
    zaznamy = ZdravotniZaznam.objects.filter(pes=pes).order_by('-datum')

    ockovani = Ockovani.objects.filter(pes=pes).order_by('-datum_ockovani')

    # Registrace fontu (v pořádku)
    font_path = os.path.join(settings.MEDIA_ROOT, 'fonts', 'DejaVuSans.ttf')
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('DejaVu Sans', font_path))

    template = get_template('users/pdf_sablona.html')

    # Context - sem musíme dát VŠE, co chceme v PDF vidět
    context = {
        'pes': pes,
        'posledni_zaznamy': zaznamy,
        'ockovani_list': ockovani,  # Přidáno do contextu
        'media_root': settings.MEDIA_ROOT,
    }

    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="export_{pes.jmeno}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response, encoding='utf-8', link_callback=link_callback)
    return response



def nahrat_rodokmen(request, pes_id):
    if request.method == 'POST':
        # 1. Získáme profil majitele (opraveno na pole 'uzivatel' dle tvého modelu)
        # Používáme get_object_or_404, aby kód nespadl, pokud profil neexistuje
        profil = get_object_or_404(ProfilMajitele, uzivatel=request.user)

        # 2. Najdeme konkrétního psa, který patří tomuto profilu
        pes = get_object_or_404(Pes, id=pes_id, majitel=profil)

        # 3. Aktualizujeme textová pole (otec/matka), pokud jsou v POST datech
        if 'otec_manualni' in request.POST:
            pes.otec_manualni = request.POST.get('otec_manualni')

        if 'matka_manualni' in request.POST:
            pes.matka_manualni = request.POST.get('matka_manualni')

        # 4. Zpracujeme nahraný soubor PDF
        if 'rodokmen_pdf' in request.FILES:
            # Smaže starý soubor, pokud existuje (volitelné, ale doporučené pro pořádek)
            if pes.rodokmen_pdf:
                pes.rodokmen_pdf.delete(save=False)

            pes.rodokmen_pdf = request.FILES['rodokmen_pdf']

        # 5. Vše uložíme do databáze
        pes.save()

    # 6. Přesměrujeme zpět na detail psa (název URL cesty, ne .html soubor)
    return redirect('detail_psa', pes_id=pes_id)

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
def pridat_polozku_vse(request, typ_kategorie, zviratko_typ='pes'):
    # Logika titulků a nápověd
    if typ_kategorie == 'vystavy':
        placeholder_text = "Např. Mezinárodní výstava psů Praha 2026"
        titul = "Nová Výstava"
    elif typ_kategorie == 'lovecka':
        placeholder_text = "Např. Barvářské zkoušky honičů"
        titul = "Nová Akce"
    else:
        placeholder_text = "Např. Britská krátkosrstá" if zviratko_typ == 'kocka' else "Např. Zlatý retrívr"
        titul = f"Nové plemeno ({'Kočka' if zviratko_typ == 'kocka' else 'Pes'})"

    if request.method == 'POST':
        form = PlemenoForm(request.POST, request.FILES)
        if form.is_valid():
            plemeno = form.save(commit=False)
            plemeno.kategorie = typ_kategorie

            # Ošetření názvu pro kočky proti duplicitě
            if zviratko_typ == 'kocka':
                nizky_nazev = plemeno.nazev.lower()
                if 'kočka' not in nizky_nazev and 'kocka' not in nizky_nazev:
                    plemeno.nazev = f"Kočka {plemeno.nazev}"

            plemeno.slug = slugify(plemeno.nazev)
            plemeno.save()
            return redirect('seznam_zdi')
        # Pokud form není validní, Django vypíše chyby do form.errors
    else:
        form = PlemenoForm()

    # TENTO ŘÁDEK JE KLÍČOVÝ: Nastaví nápovědu i po neúspěšném odeslání
    form.fields['nazev'].widget.attrs['placeholder'] = placeholder_text

    return render(request, 'users/pridat_polozku.html', {
        'form': form,
        'titul': titul,
        'zviratko_typ': zviratko_typ,
        'info': {'typ': zviratko_typ, 'titul': titul}
    })


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
    # Načteme psa, jinak vyhodíme 404
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

        # Získání dat z POST (ujisti se, že názvy odpovídají <input name="..."> v HTML)
        # Pokud v modalu nemáš pole 'typ', dosadíme výchozí 'vystava'
        typ_zaznamu = request.POST.get('typ', 'vystava')
        nazev_akce = request.POST.get('nazev')
        oceneni_text = request.POST.get('oceneni')
        datum_akce = request.POST.get('datum')

        Uspech.objects.create(
            pes=pes,
            typ=typ_zaznamu,
            nazev=nazev_akce,
            oceneni=oceneni_text,
            datum=datum_akce if datum_akce else timezone.now().date()
        )
        return redirect('detail_psa', pes_id=pes.id)
    return redirect('detail_psa', pes_id=pes_id)


@login_required
def smazat_uspech(request, uspech_id):
    uspech = get_object_or_404(Uspech, id=uspech_id)
    pes_id = uspech.pes.id

    # Kontrola, zda je uživatel majitelem psa
    if uspech.pes.majitel == request.user or request.user.is_superuser:
        uspech.delete()

    return redirect('kariera_psa', pes_id=pes_id)


# Tato funkce zobrazí stránku se seznamem všech vrhů
def vrhy_psa(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id)
    # Získáme všechny vrhy pro tohoto psa
    vrhy = Vrh.objects.filter(rodic=pes).order_by('-datum_narozeni')

    # Změnil jsem název šablony na vrhy_psa.html,
    # protože tu v detailu psa už odkazuješ (a TemplateDoesNotExist ti zmizí)
    return render(request, 'users/pridat_vrh.html', {'pes': pes, 'vrhy': vrhy})


# Tato funkce zpracuje odeslání modalu z detailu psa
def pridat_vrh(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id)

    if request.method == 'POST':
        Vrh.objects.create(
            rodic=pes,
            datum_narozeni=request.POST.get('datum_narozeni'),
            oznaceni_vrhu=request.POST.get('oznaceni_vrhu'),
            pocet_psu=request.POST.get('pocet_psu', 0),
            pocet_fen=request.POST.get('pocet_fen', 0),
            druhy_rodic=request.POST.get('druhy_rodic'),
            poznamka=request.POST.get('poznamka')
        )
    return redirect('detail_psa', pes_id=pes.id)


@login_required
def chovnost_psa(request, pes_id):
    """Zobrazí stránku s detaily o chovnosti, RTG a testech."""
    pes = get_object_or_404(Pes, id=pes_id)
    return render(request, 'users/chovnost_psa.html', {
        'pes': pes,
        'je_majitel': pes.majitel == request.user
    })


@login_required
def upravit_chovnost(request, pes_id):
    """Zpracuje formulář pro aktualizaci chovnosti, bonitace a testů."""
    pes = get_object_or_404(Pes, id=pes_id, majitel=request.user)

    if request.method == 'POST':
        # Načtení dat z formuláře (ujisti se, že name v HTML odpovídá těmto klíčům)
        pes.chovnost = request.POST.get('chovnost')
        pes.bonitace = request.POST.get('bonitace')
        pes.zdravotni_testy = request.POST.get('zdravotni_testy')

        # Pokud máš v modelu pole pro RTG (např. DKK, DLK)
        pes.dkk = request.POST.get('dkk')
        pes.dlk = request.POST.get('dlk')

        pes.save()
        return redirect('detail_psa', pes_id=pes.id)

    return render(request, 'users/upravit_chovnost.html', {'pes': pes})

@login_required
def seznam_notifikaci(request):
    profil = request.user.profil
    nots_list = []
    dnes = timezone.now().date()

    # --- 1. ZDRAVOTNÍ LOGIKA ---
    psi = profil.psi.all()
    for pes in psi:
        kontroly = [
            (pes.posledni_ockovani, 365, 'očkování', 'fas fa-syringe'),
            (pes.posledni_odcerveni, 90, 'odčervení', 'fas fa-tablets'),
            (pes.posledni_klistata, 30, 'antiparazitika', 'fas fa-bug'),
        ]
        for posledni_datum, dny_platnosti, nazev, ikona in kontroly:
            if posledni_datum:
                termin = posledni_datum + timedelta(days=dny_platnosti)
                if termin <= dnes + timedelta(days=14):
                    nots_list.append({
                        'typ': 'zdravi_urgent',
                        'pes': pes,
                        'text': f'Blíží se termín pro {nazev} u mazlíčka {pes.jmeno}!',
                        'datum_vytvoreni': timezone.now(),
                        'urgent': True,
                        'ikona_zdravi': ikona
                    })

    # --- 2. SOCIÁLNÍ LOGIKA ---
    db_notifications = Notifikace.objects.filter(prijemce=request.user)
    for n in db_notifications:
        nots_list.append(n)

    # --- 3. MOJE AKTIVITA (Příspěvky) ---
    # Pole je 'datum_pridani'
    moje_prispevky = Prispevek.objects.filter(autor=request.user).order_by('-datum_pridani')
    for p in moje_prispevky:
        nots_list.append({
            'typ': 'moje_aktivita',
            'text': f'Publikovala jsi příspěvek: "{p.text[:40]}..."',
            'datum_vytvoreni': p.datum_pridani,
            'prispevek': p,
            'moje': True
        })

    # --- 4. MOJE INZERCE (Bazar) ---
    # Pole je 'vytvoreno'
    moje_inzeraty = Inzerat.objects.filter(autor=request.user).order_by('-vytvoreno')
    for i in moje_inzeraty:
        nots_list.append({
            'typ': 'moje_inzerce',
            'text': f'Tvůj inzerát "{i.titulek}" je vystaven v bazaru.',
            'datum_vytvoreni': i.vytvoreno,
            'inzerat': i,
            'moje': True
        })
    # --- 5. MOJE RECENZE
    moje_recenze = Recenze.objects.filter(uzivatel=request.user).order_by('-vytvoreno')
    for r in moje_recenze:
        nots_list.append({
            'typ': 'moje_recenze',
            'text': f'Napsala jsi recenzi ({r.hvezdy}⭐) pro: {r.sluzba.nazev}',
            'datum_vytvoreni': r.vytvoreno,
            'recenze': r,
            'moje': True,
            'odesilatel': request.user
        })

    # --- 6. SEŘAZENÍ ---
    nots_list.sort(
        key=lambda x: x.datum_vytvoreni if hasattr(x, 'datum_vytvoreni') else x.get('datum_vytvoreni', timezone.now()),
        reverse=True
    )

    # --- 7. PAGINACE ---
    paginator = Paginator(nots_list, 10)  #
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'users/notifikace.html', {
        'nots': page_obj,
    })

@login_required
def smazat_notifikaci(request, pk):
    notifikace = get_object_or_404(Notifikace, pk=pk, prijemce=request.user)
    notifikace.delete()
    return redirect('seznam_notifikaci')

@login_required
def smazat_vsechny_notifikace(request):
    Notifikace.objects.filter(prijemce=request.user).delete()
    return redirect('seznam_notifikaci')