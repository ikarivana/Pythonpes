import os
import json
import io
from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from .models import Pes, ProfilMajitele

from xhtml2pdf import pisa
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from pes import settings

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

# Importy tvých modelů a formulářů
from .models import (
    Pes, ProfilMajitele, Plemeno, Prispevek, Komentar,
    ZdravotniZaznam, Uspech, Notifikace, Ockovani,
    Galerie, Video
)
from .forms import (
    PesForm, PrispevekForm, PlemenoForm, OckovaniForm,
    UserUpdateForm, ExtendedRegistrationForm
)

# --- 1. SPRÁVA PSŮ (Základní operace) ---

@login_required
def seznam_psu(request):
    profil, created = ProfilMajitele.objects.get_or_create(uzivatel=request.user)

    # 2. TEĎ už ho můžeme v klidu vypsat do terminálu pro kontrolu
    print(f"DEBUG: Uživatel {request.user.username} má premium: {profil.is_premium}")

    psi = Pes.objects.filter(majitel=profil)
    return render(request, 'users/seznam_psu.html', {'psi': psi, 'profil': profil})

@login_required
def pridat_psa(request):
    profil, created = ProfilMajitele.objects.get_or_create(uzivatel=request.user)

    if not profil.is_premium and not request.user.is_staff and profil.psi.count() >= 1:
        messages.warning(request, "Ve verzi zdarma můžete mít pouze jednoho pejska.")
        return redirect('seznam_psu')

    if request.method == 'POST':
        request_files = request.FILES.copy()
        if 'fotka' in request_files:
            try:
                img_file = request_files['fotka']
                img = Image.open(img_file)
                img = ImageOps.exif_transpose(img)
                if img.mode in ("RGBA", "P", "CMYK"):
                    img = img.convert("RGB")
                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                temp_handle = io.BytesIO()
                img.save(temp_handle, format='JPEG', quality=85)
                temp_handle.seek(0)
                novy_nazev = img_file.name.rsplit('.', 1)[0] + ".jpg"
                request_files['fotka'] = ContentFile(temp_handle.read(), name=novy_nazev)
            except Exception as e:
                print(f"Chyba zpracování: {e}")

        form = PesForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            pes = form.save(commit=False)
            pes.majitel = profil
            pes.save()
            messages.success(request, f"Pejsek {pes.jmeno} přidán!")
            return redirect('seznam_psu')
    else:
        form = PesForm(request=request)
    return render(request, 'users/pridat_psa.html', {'form': form})

@login_required
def upravit_psa(request, pk):
    # 1. Najdeme psa
    pes = get_object_or_404(Pes, pk=pk, majitel=request.user.profil)

    if request.method == 'POST':
        # 2. Aktualizujeme jen pole, která přišla (prevence IntegrityError)
        if 'jmeno' in request.POST: pes.jmeno = request.POST.get('jmeno')
        if 'rasa' in request.POST: pes.rasa = request.POST.get('rasa')
        if 'cip' in request.POST: pes.cip = request.POST.get('cip')
        if 'popis' in request.POST: pes.popis = request.POST.get('popis')
        if 'cislo_zapisu' in request.POST: pes.cislo_zapisu = request.POST.get('cislo_zapisu')
        if 'rtg_hd' in request.POST: pes.rtg_hd = request.POST.get('rtg_hd')
        if 'rtg_ed' in request.POST: pes.rtg_ed = request.POST.get('rtg_ed')

        # Data (Datumy)
        narozeni = request.POST.get('datum_narozeni')
        if narozeni: pes.datum_narozeni = narozeni
        ocko = request.POST.get('posledni_ockovani')
        if ocko: pes.posledni_ockovani = ocko

        # Fotka
        if request.FILES.get('fotka'):
            pes.fotka = request.FILES.get('fotka')

        # 3. Režim ztráty (Důležité pro ten přepínač v detailu)
        if 'je_ztraceny_sent' in request.POST or 'jmeno' in request.POST:
            pes.je_ztraceny = 'je_ztraceny' in request.POST

        pes.save()
        messages.success(request, f"Změny u psa {pes.jmeno} byly úspěšně uloženy.")

        # TADY BYLA CHYBA: Musí tu být pes_id, ne pk!
        return redirect('detail_psa', pes_id=pes.id)

    # 4. TENTO KÓD MUSÍ BÝT ODSZENÝ TAKTO (pro zobrazení stránky - GET)
    fotky = pes.galerie_fotky.all()
    videa = pes.galerie_videa.all()

    return render(request, 'users/upravit_psa.html', {
        'pes': pes,
        'fotky': fotky,
        'videa': videa
    })

@login_required
def smazat_psa(request, pk):
    pes = get_object_or_404(Pes, pk=pk, majitel=request.user.profil)
    if request.method == 'POST':
        pes.delete()
        return redirect('seznam_psu')
    return render(request, 'users/smazat_psa_potvrzeni.html', {'pes': pes})

# --- 2. MULTIMÉDIA (Galerie - Nahrávání a mazání) ---

@login_required
def pridat_foto(request, pes_id):
    if request.method == 'POST':
        pes = get_object_or_404(Pes, id=pes_id, majitel=request.user.profil)
        profil = request.user.profil

        # KONTROLA LIMITU FOTEK (5 fotek pro Free)
        if not profil.je_premium and not request.user.is_staff:
            if pes.galerie_fotky.count() >= 5:
                messages.warning(request, "V bezplatné verzi můžete mít u pejska maximálně 5 fotek.")
                return redirect('upravit_psa', pk=pes_id)

        img = request.FILES.get('obrazek')
        if img:
            try:
                zpracovany_obrazek = zpracuj_foto(img)
                Galerie.objects.create(pes=pes, obrazek=zpracovany_obrazek)
                messages.success(request, "Fotka nahrána.")
            except Exception as e:
                messages.error(request, f"Chyba: {e}")

    return redirect('upravit_psa', pk=pes_id)

@login_required
def smazat_foto(request, pk):
    # Najdeme fotku a zároveň ověříme, že patří psovi aktuálního uživatele
    foto = get_object_or_404(Galerie, id=pk, pes__majitel=request.user.profil)
    pes_id = foto.pes.id  # Uložíme si ID psa, abychom se měli kam vrátit
    foto.delete()         # Smažeme záznam z databáze (i soubor z disku, pokud máš správně nastaveno)
    messages.success(request, "Fotka byla úspěšně smazána.")
    return redirect('detail_psa', pes_id=pes_id)


@login_required
def pridat_video(request, pes_id):
    if request.method == 'POST':
        pes = get_object_or_404(Pes, id=pes_id, majitel=request.user.profil)
        profil = request.user.profil

        # KONTROLA LIMITU VIDEÍ (1 video pro Free)
        if not profil.je_premium and not request.user.is_staff:
            if pes.galerie_videa.count() >= 1:
                messages.warning(request, "V bezplatné verzi můžete mít u pejska pouze 1 video.")
                return redirect('upravit_psa', pk=pes_id)

        vid = request.FILES.get('video_soubor')
        if vid:
            Video.objects.create(pes=pes, video_soubor=vid)
            messages.success(request, "Video nahráno.")

    return redirect('upravit_psa', pk=pes_id)
@login_required
def smazat_video(request, pk):
    video = get_object_or_404(Video, id=pk, pes__majitel=request.user.profil)
    p_id = video.pes.id
    video.delete()
    messages.success(request, "Video smazáno.")
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
        'ockovani': pes.ockovani.all() if hasattr(pes, 'ockovani') else [],
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
def prepnout_ztratu(request, pk):
    pes = get_object_or_404(Pes, pk=pk, majitel=request.user.profil)
    pes.je_ztraceny = not pes.je_ztraceny
    pes.save()
    return redirect('detail_psa', pes_id=pk)

@csrf_exempt
def odeslat_polohu_nalezu(request, pes_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        lat, lng = data.get('lat'), data.get('lng')
        pes = get_object_or_404(Pes, id=pes_id)
        map_url = f"https://www.google.com/maps?q={lat},{lng}"
        zprava = f"QR kód pejska {pes.jmeno} byl naskenován. Poloha: {map_url}"
        send_mail("📍 POLOHA NÁLEZU", zprava, 'noreply@pes.cz', [pes.majitel.uzivatel.email])
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)

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

    # TADY vytváříme font_path - musí to být PŘEDTÍM, než ji použiješ
    font_path = os.path.join(settings.MEDIA_ROOT, 'fonts', 'DejaVuSans.ttf')

    print(f"--- CESTA K FONTU: {font_path} ---")
    print(f"--- EXISTUJE SOUBOR?: {os.path.exists(font_path)} ---")

    # Teď už font_path nebude červená, protože už existuje
    pdfmetrics.registerFont(TTFont('MojeCestina', font_path))

    template = get_template('users/pdf_sablona.html')

    context = {
        'pes': pes,
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

# --- 5. SOCIÁLNÍ SÍŤ A OSTATNÍ ---

def seznam_zdi(request):
    return render(request, 'users/social_zed.html', {'vsechna_plemena': Plemeno.objects.all().order_by('nazev')})

def zed_plemene(request, slug):
    plemeno = get_object_or_404(Plemeno, slug=slug)
    prispevky = plemeno.prispevky_na_zed.all().order_by('-datum_pridani')
    return render(request, 'users/zed.html', {'plemeno': plemeno, 'prispevky': prispevky, 'form': PrispevekForm()})


@login_required
def profil_uzivatele(request):
    profil, created = ProfilMajitele.objects.get_or_create(uzivatel=request.user)
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
            return redirect('seznam_psu')
    else:
        form = ExtendedRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

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
    return render(request, 'users/pridat_prispevek.html', {'form': form, 'editace': True})

@login_required
def smazat_prispevek(request, pk):
    prispevek = get_object_or_404(Prispevek, pk=pk, autor=request.user)
    slug = prispevek.plemeno.slug
    if request.method == 'POST':
        prispevek.delete()
        messages.success(request, "Příspěvek byl smazán.")
        return redirect('zed_plemene', slug=slug)
    return render(request, 'users/smazat_potvrzeni.html', {'objekt': prispevek})

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
        Komentar.objects.create(
            prispevek=parent.prispevek,
            autor=request.user,
            text=request.POST.get('text_odpovedi'),
        )
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def seznam_notifikaci(request):
    nots = request.user.prijate_notifikace.all().order_by('-datum_vytvoreni')
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


@login_required
def upravit_profil(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Váš profil byl úspěšně aktualizován.")
            return redirect('profil_uzivatele')
    else:
        form = UserUpdateForm(instance=request.user)

    return render(request, 'users/upravit_profil.html', {'form': form})