import os
import json
import io
from datetime import timedelta, timezone
from django.core.files import File

import qrcode
from PIL import Image
from pillow_heif import register_heif_opener

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.template.loader import get_template
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile

from .forms import UserUpdateForm, PlemenoForm, PrispevekForm, ExtendedRegistrationForm, OckovaniForm, PesForm
from .models import Plemeno, Prispevek, Komentar, GalerieFotka, GalerieVideo, ProfilMajitele, Uspech, Pes, \
    ZdravotniZaznam, Notifikace

# Ostatní nástroje
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
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

# --- 1. SPRÁVA PSŮ (Základní operace) ---

@login_required
def seznam_psu(request):
    profil, created = ProfilMajitele.objects.get_or_create(uzivatel=request.user)

    # 2. TEĎ už ho můžeme v klidu vypsat do terminálu pro kontrolu
    print(f"DEBUG: Uživatel {request.user.username} má premium: {profil.is_premium}")

    psi = Pes.objects.filter(majitel=profil)
    return render(request, 'users/seznam_psu.html', {'psi': psi, 'profil': profil})


@login_required
def dashboard(request):
    profil = request.user.profil
    psi = Pes.objects.filter(majitel=profil)
    # Načteme nepřečtené notifikace (sociální i zdravotní)
    nots = request.user.prijate_notifikace.filter(precteno=False).order_by('-datum_vytvoreni')
    dnes_plus_3 = timezone.now().date() + timedelta(days=3)

    return render(request, 'users/dashboard.html', {
        'psi': psi,
        'nots': nots,
        'profil': profil,
        'dnes_plus_3': dnes_plus_3,
    })


@login_required
def pridat_psa(request):
    profil = get_object_or_404(ProfilMajitele, uzivatel=request.user)

    # 1. Kontrola limitu pro neplatiče
    if not profil.is_premium and not request.user.is_staff and profil.psi.count() >= 1:
        messages.warning(request, "Ve verzi zdarma můžete mít pouze jednoho pejska.")
        return redirect('seznam_psu')

    if request.method == 'POST':
        form = PesForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            try:
                pes = form.save(commit=False)
                pes.majitel = profil

                # Zpracování fotky
                if 'fotka' in request.FILES:
                    pes.fotka = zpracuj_foto(request.FILES['fotka'])

                # Automatické vyplnění prázdných polí (aby formulář prošel)
                # PŘIDAL JSEM SEM I TYP OCHRANY PRO KLÍŠŤATA
                for pole in ['otec_manualni', 'matka_manualni', 'zdravotni_testy', 'bonitace', 'typ_ochrany_klistata']:
                    if hasattr(pes, pole) and not getattr(pes, pole):
                        setattr(pes, pole, "Nezadáno")

                pes.save()

                # Generování QR (zůstává stejné)
                url_psa = f"https://epes.online/users/pes/{pes.id}/"
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(url_psa)
                qr.make(fit=True)
                img_qr = qr.make_image(fill_color="black", back_color="white")
                buffer = io.BytesIO()
                img_qr.save(buffer, format='PNG')
                filename = f'qr_{pes.id}_{slugify(pes.jmeno)}.png'
                pes.qr_kod.save(filename, ContentFile(buffer.getvalue()), save=True)

                messages.success(request, f"Pejsek {pes.jmeno} byl úspěšně přidán!")
                return redirect('seznam_psu')

            except Exception as e:
                messages.error(request, f"Kritická chyba při ukládání: {e}")
                print(f"DEBUG EXCEPTION: {e}")
        else:
            # TADY JE TA DŮLEŽITÁ ČÁST: Pokud formulář není validní, vypíše to chyby do konzole
            print(f"CHYBY FORMULÁŘE: {form.errors}")
            messages.error(request, "Formulář obsahuje chyby. Zkontrolujte vyplněná pole.")
    else:
        form = PesForm(request=request)

    return render(request, 'users/pridat_psa.html', {'form': form})


@login_required
def upravit_psa(request, pk):
    pes = get_object_or_404(Pes, pk=pk, majitel=request.user.profil)

    if request.method == 'POST':
        form = PesForm(request.POST, request.FILES, instance=pes, request=request)
        # Přidáme kontrolu, jestli uživatel zaškrtl "Opravit QR kód"
        opravit_qr = request.POST.get('regenerovat_qr') == 'on'

        if form.is_valid():
            try:
                pes_upraveny = form.save(commit=False)

                if 'fotka' in request.FILES:
                    pes_upraveny.fotka = zpracuj_foto(request.FILES['fotka'])

                # QR KÓD SE PŘEGENERUJE JEN KDYŽ UŽIVATEL CHCE
                if opravit_qr or not pes_upraveny.qr_kod:
                    url_psa = f"https://epes.online/users/pes/{pes_upraveny.id}/"
                    qr = qrcode.QRCode(version=1, box_size=10, border=5)
                    qr.add_data(url_psa)
                    qr.make(fit=True)

                    img_qr = qr.make_image(fill_color="black", back_color="white")
                    buffer = io.BytesIO()
                    img_qr.save(buffer, format='PNG')

                    if pes_upraveny.qr_kod:
                        pes_upraveny.qr_kod.delete(save=False)

                    filename = f'qr_{pes_upraveny.id}_{slugify(pes_upraveny.jmeno)}.png'
                    pes_upraveny.qr_kod.save(filename, ContentFile(buffer.getvalue()), save=False)

                for pole in ['otec_manualni', 'matka_manualni', 'zdravotni_testy', 'bonitace']:
                    if hasattr(pes_upraveny, pole) and not getattr(pes_upraveny, pole):
                        setattr(pes_upraveny, pole, "Nezadáno")

                pes_upraveny.save()
                messages.success(request, f"Údaje pejska {pes_upraveny.jmeno} byly upraveny.")
                return redirect('seznam_psu')
            except Exception as e:
                messages.error(request, f"Chyba při ukládání: {e}")
    else:
        form = PesForm(instance=pes, request=request)

    return render(request, 'users/upravit_psa.html', {'form': form, 'pes': pes})

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
    if request.method == 'POST':
        pes = get_object_or_404(Pes, id=pes_id, majitel=request.user.profil)
        profil = request.user.profil

        # KONTROLA LIMITU FOTEK (5 fotek pro Free)
        if not profil.is_premium and not request.user.is_staff:
            if pes.galerie_fotky.count() >= 5:
                messages.warning(request, "V bezplatné verzi můžete mít u pejska maximálně 5 fotek.")
                return redirect('upravit_psa', pk=pes_id)

        img = request.FILES.get('obrazek')
        if img:
            try:
                zpracovany_obrazek = zpracuj_foto(img)
                # ZMĚNA: Galerie -> GalerieFotka
                GalerieFotka.objects.create(pes=pes, obrazek=zpracovany_obrazek)
                messages.success(request, "Fotka nahrána.")
            except Exception as e:
                messages.error(request, f"Chyba: {e}")

    return redirect('upravit_psa', pk=pes_id)

@login_required
def smazat_foto(request, pk):
    # Přidána kontrola, aby se předešlo NoReverseMatch
    foto = get_object_or_404(GalerieFotka, id=pk, pes__majitel=request.user.profil)
    pes_id = foto.pes.id
    foto.delete()
    messages.success(request, "Fotka byla úspěšně smazána.")
    # Vracíme se zpět do editoru, ne na detail (který může zlobit v URL)
    return redirect('upravit_psa', pk=pes_id)


@login_required
def pridat_video(request, pes_id):
    if request.method == 'POST':
        pes = get_object_or_404(Pes, id=pes_id, majitel=request.user.profil)
        profil = request.user.profil

        # KONTROLA LIMITU VIDEÍ (1 video pro Free)
        if not profil.is_premium and not request.user.is_staff:
            if pes.galerie_videa.count() >= 1:
                messages.warning(request, "V bezplatné verzi můžete mít u pejska pouze 1 video.")
                return redirect('upravit_psa', pk=pes_id)

        vid = request.FILES.get('video_soubor')
        if vid:
            # ZMĚNA: Video -> GalerieVideo
            GalerieVideo.objects.create(pes=pes, video_soubor=vid)
            messages.success(request, "Video nahráno.")

    return redirect('upravit_psa', pk=pes_id)

@login_required
def smazat_video(request, pk):
    video = get_object_or_404(GalerieVideo, id=pk, pes__majitel=request.user.profil)
    p_id = video.pes.id
    video.delete()
    messages.success(request, "Video smazáno.")
    # Sjednoceno na 'pk', aby to odpovídalo vašim URL patternům
    return redirect('upravit_psa', pk=p_id)


# --- 3. DETAIL, SOS A POLOHA ---
def detail_psa(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id)

    # --- INTELIGENTNÍ VÝHYBKA ---
    # Pokud prohlížející NENÍ majitel, uvidí jen SOS kartu
    if not request.user.is_authenticated or pes.majitel.uzivatel != request.user:
        return render(request, 'users/nouzovy_profil.html', {
            'pes': pes,
            'majitel': pes.majitel,
            'nouzovy_rezim': pes.je_ztraceny,
        })

    # Pokud jsi to ty (majitel), vidíš svůj plný deník
    return render(request, 'users/detail_psa.html', {
        'pes': pes,
        'uspechy': pes.uspechy.all(),
        'fotky': pes.galerie_fotky.all(),
        'videa': pes.galerie_videa.all(),
        'ockovani': pes.vsechna_ockovani.all(),
    })

def nouzovy_profil_psa(request, pes_id):
    # Tato funkce je tu teď jako pojistka pro přímé URL /pes/2/
    pes = get_object_or_404(Pes, id=pes_id)
    return render(request, 'users/nouzovy_profil.html', {
        'pes': pes,
        'majitel': pes.majitel,
        'nouzovy_rezim': pes.je_ztraceny,
    })


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


@login_required
def prepnout_ztratu(request, pes_id):
    pes = get_object_or_404(Pes, pk=pes_id, majitel=request.user.profil)
    pes.je_ztraceny = not pes.je_ztraceny
    pes.save()

    return redirect('detail_psa', pes_id=pes_id)


@csrf_exempt
def odeslat_polohu_nalezu(request, pes_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        lat, lng = data.get('lat'), data.get('lng')
        pes = get_object_or_404(Pes, id=pes_id)

        # TATO PODMÍNKA JE KLÍČOVÁ:
        if pes.je_ztraceny:
            map_url = f"https://www.google.com/maps?q={lat},{lng}"
            zprava = f"QR kód pejska {pes.jmeno} byl naskenován. Poloha: {map_url}"

            send_mail(
                "📍 POLOHA NÁLEZU",
                zprava,
                'noreply@pes.cz',
                [pes.majitel.uzivatel.email]
            )
            return JsonResponse({'status': 'email_odeslan'})

        # Pokud pes není ztracený, jen potvrdíme příjem polohy, ale nic neposíláme
        return JsonResponse({'status': 'pes_neni_ztracen_nic_neposlano'})

    return JsonResponse({'status': 'error'}, status=400)

def seznam_hledanych_psu(request):
    # Vyfiltruje pouze psy, kteří jsou označeni jako ztracení
    hledani_psi = Pes.objects.filter(je_ztraceny=True).order_by('-id')
    return render(request, 'users/seznam_hledanych.html', {'psi': hledani_psi})

# --- 4. ZDRAVÍ A PDF ---

@login_required
def veterinar(request):
    profil = request.user.profil
    if request.method == 'POST':
        pes = get_object_or_404(Pes, id=request.POST.get('pes_id'), majitel=profil)
        ZdravotniZaznam.objects.create(pes=pes, titulek=request.POST.get('titulek'), popis=request.POST.get('popis'))
    return render(request, 'users/veterinar.html', {
        'psi': profil.psi.all(),
        'posledni_zaznamy': ZdravotniZaznam.objects.filter(pes__majitel=profil).order_by('-datum_vytvoreni')
    })


@login_required
def pridat_ockovani(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id, majitel__uzivatel=request.user)
    if request.method == 'POST':
        form = OckovaniForm(request.POST)
        if form.is_valid():
            ockovani = form.save(commit=False)
            ockovani.pes = pes
            ockovani.save()
            messages.success(request, f"Očkování pro psa {pes.jmeno} bylo uloženo.")
            return redirect('detail_psa', pes_id=pes.id)
    else:
        form = OckovaniForm()

    return render(request, 'users/pridat_ockovani.html', {
        'form': form,
        'pes': pes
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
    pes = get_object_or_404(Pes, id=pes_id, majitel=request.user.profil)

    # Definice cesty k fontu
    font_path = os.path.join(settings.MEDIA_ROOT, 'fonts', 'DejaVuSans.ttf')

    # Kontrola pro tebe do terminálu
    print(f"--- CESTA K FONTU: {font_path} ---")
    print(f"--- EXISTUJE SOUBOR?: {os.path.exists(font_path)} ---")

    # REGISTRACE: Název 'DejaVu Sans' musí být PŘESNĚ jako v HTML šabloně
    pdfmetrics.registerFont(TTFont('DejaVu Sans', font_path))

    template = get_template('users/pdf_sablona.html')

    context = {
        'pes': pes,
        'media_root': settings.MEDIA_ROOT, # Předáváme absolutní cestu pro link_callback
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

# --- 5. SOCIÁLNÍ SÍŤ A OSTATNÍ ---

def seznam_zdi(request):
    return render(request, 'users/social_zed.html', {'vsechna_plemena': Plemeno.objects.all().order_by('nazev')})


def zed_plemene(request, slug):
    plemeno = Plemeno.objects.filter(slug=slug).first()
    # Tady byla ta chyba - změň plemeno_slug na sekce_slug
    prispevky = Prispevek.objects.filter(sekce_slug=slug).order_by('-datum_pridani')

    form = PrispevekForm()

    if request.method == 'POST' and 'btn_prispevek' in request.POST:
        form = PrispevekForm(request.POST, request.FILES)
        if form.is_valid():
            prispevek = form.save(commit=False)
            prispevek.autor = request.user
            prispevek.plemeno = plemeno
            prispevek.sekce_slug = slug  # Tady se to uloží správně
            prispevek.save()
            return redirect('zed_plemene', slug=slug)

    return render(request, 'users/zed.html', {
        'form': form,  # Toto zajistí zobrazení pole
        'plemeno': plemeno,
        'prispevky': prispevky,
        'nazev_sekce': plemeno.nazev if plemeno else slug.capitalize(),
        'slug': slug
    })


@login_required
def smazat_prispevek(request, post_id):
    prispevek = get_object_or_404(Prispevek, id=post_id)
    # Kontrola, že maže jen autor
    if prispevek.autor == request.user:
        slug = prispevek.sekce_slug
        prispevek.delete()
        messages.success(request, "Příspěvek smazán.")
        return redirect('zed_plemene', slug=slug)
    return HttpResponseForbidden()

@login_required
def profil_uzivatele(request):
    profil, created = ProfilMajitele.objects.get_or_create(uzivatel=request.user)
    # Získání psů přes related_name='psi', pokud ho máš v modelu
    # Pokud ne, použij: request.user.pes_set.all()
    context = {
        'profil': profil,
        'libi_se_mi': [],
        'komentare': [],
    }
    return render(request, 'users/profil.html', context)

def register(request):
    if request.method == 'POST':
        form = ExtendedRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Změna z 'muj_profil' na 'profil' podle vašeho urls.py
            return redirect('profil')
    else:
        form = ExtendedRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def upravit_profil(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil byl úspěšně upraven.")
            return render(request, 'users/upravit_profil.html', {'form': form})
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'users/profil.html', {'form': form}) # Upravujeme přímo v profilu

@login_required
def smazat_profil(request):
    # Tohle je ta klíčová funkce, která ti chyběla!
    uzivatel = request.user
    logout(request)
    uzivatel.delete()
    messages.warning(request, "Tvůj účet byl smazán.")
    return redirect('home')


# --- DOPLNĚK: ÚSPĚCHY ---
@login_required
def pridat_uspech(request, pes_id):
    pes = get_object_or_404(Pes, id=pes_id, majitel__uzivatel=request.user)
    if request.method == 'POST':
        Uspech.objects.create(
            pes=pes,
            nazev=request.POST.get('nazev'),
            typ=request.POST.get('typ'),
            datum=request.POST.get('datum') or None
        )
        messages.success(request, "Úspěch byl přidán.")
    return redirect('detail_psa', pes_id=pes.id)

# --- DOPLNĚK: SOCIÁLNÍ SÍŤ (Příspěvky a interakce) ---

@login_required
def upravit_prispevek(request, pk):
    p = get_object_or_404(Prispevek, pk=pk, autor=request.user)
    if request.method == 'POST':
        form = PrispevekForm(request.POST, request.FILES, instance=p)
        if form.is_valid():
            form.save()
            return redirect('zed_plemene', slug=p.plemeno.slug)
    else:
        form = PrispevekForm(instance=p)
    return redirect('zed_plemene', slug=p.plemeno.slug if p.plemeno else p.sekce_slug)

@login_required
def smazat_prispevek(request, pk):
    prispevek = get_object_or_404(Prispevek, pk=pk, autor=request.user)
    slug = prispevek.plemeno.slug
    if request.method == 'POST':
        prispevek.delete()
        messages.success(request, "Příspěvek byl smazán.")
        return redirect('zed_plemene', slug=slug)
    # TADY CHYBÍ NÁVRAT (např. redirect zpět, pokud uživatel jen klikne na URL bez POSTu)
    return redirect('zed_plemene', slug=slug)

@login_required
def pridej_like(request, post_id):
    p = get_object_or_404(Prispevek, id=post_id)
    if request.user in p.likes.all():
        p.likes.remove(request.user)
    else:
        p.likes.add(request.user)
        if p.autor != request.user:
            Notifikace.objects.create(
                prijemce=p.autor,
                odesilatel=request.user,
                typ='like',
                prispevek=p
            )
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def pridat_odpoved(request, parent_id):
    parent = get_object_or_404(Komentar, id=parent_id)
    if request.method == "POST":
        novy_komentar = Komentar.objects.create(
            prispevek=parent.prispevek,
            autor=request.user,
            text=request.POST.get('text_odpovedi'),
        )
        # TADY pošli notifikaci autorovi původního komentáře
        if parent.autor != request.user:
            Notifikace.objects.create(
                prijemce=parent.autor,
                odesilatel=request.user,
                typ='odpoved',
                prispevek=parent.prispevek
            )
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def seznam_notifikaci(request):
    # Načte notifikace, které uživateli přišly
    nots = request.user.prijate_notifikace.all().order_by('-datum_vytvoreni')
    # Označí je za přečtené
    nots.filter(precteno=False).update(precteno=True)
    return render(request, 'users/notifikace.html', {'nots': nots})


@login_required
def pridat_polozku_vse(request, typ_kategorie):
    if request.method == 'POST':
        form = PlemenoForm(request.POST, request.FILES)
        if form.is_valid():
            plemeno = form.save(commit=False)
            # Slug se vytvoří automaticky z názvu, pokud to máš v modelu,
            # nebo ho vytvoříme tady:
            plemeno.slug = slugify(plemeno.nazev)
            plemeno.save()
            messages.success(request, f"Položka {plemeno.nazev} byla přidána do kategorie {typ_kategorie}.")
            return redirect('seznam_zdi')
    else:
        form = PlemenoForm()

    return render(request, 'users/pridat_polozku.html', {
        'form': form,
        'typ': typ_kategorie
    })

@login_required
def upravit_komentar(request, pk):
    komentar = get_object_or_404(Komentar, id=pk, autor=request.user)
    if request.method == "POST":
        novy_text = request.POST.get('text_komentare')
        if novy_text:
            komentar.text = novy_text
            komentar.save()
            messages.success(request, "Komentář byl upraven.")
        return redirect('zed_plemene', slug=komentar.prispevek.plemeno.slug)
    return render(request, 'users/upravit_komentar.html', {'komentar': komentar})

@login_required
def smazat_komentar(request, pk):
    komentar = get_object_or_404(Komentar, id=pk)
    # Komentář může smazat buď jeho autor, nebo autor příspěvku
    if komentar.autor == request.user or komentar.prispevek.autor == request.user:
        slug = komentar.prispevek.plemeno.slug
        komentar.delete()
        messages.success(request, "Komentář byl smazán.")
        return redirect('zed_plemene', slug=slug)
    else:
        messages.error(request, "Nemáte oprávnění smazat tento komentář.")
        return redirect(request.META.get('HTTP_REFERER', '/'))


