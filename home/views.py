from django.db.models import Avg, Count
from datetime import timedelta, date
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import json
from datetime import date
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User

# Importy tvých modelů a forem
from .models import Sluzba, Recenze
from .forms import SluzbaForm, KontaktForm
from users.models import Prispevek, Pes, ProfilMajitele, Notifikace


def index(request):
    # 1. Zabezpečení proti chybám v Premium
    is_premium = False
    try:
        if request.user.is_authenticated and hasattr(request.user, 'profilmajitele'):
            profil = request.user.profilmajitele
            is_premium = profil.is_premium and (not profil.premium_do or profil.premium_do >= date.today())
    except Exception:
        is_premium = False

    # 2. Načtení dat z mapy (VYNECHÁME ZTRÁTY, ty pořešíme níže přes profily)
    limit_cas = timezone.now() - timedelta(days=7)
    try:
        # Tady přidáme .exclude(typ='ztrata'), aby se to netlouklo
        mapa_hlaseni = Sluzba.objects.filter(
            typ__in=['nebezpeci', 'navnada'],
            vytvoreno__gte=limit_cas,
            schvaleno=True
        )
    except Exception:
        mapa_hlaseni = []

    # 3. Načtení ztracených psů (SOS profily - ty s fotkou)
    try:
        ztraceni_mazlicci = Pes.objects.filter(je_ztraceny=True)
    except Exception:
        ztraceni_mazlicci = []

    krizova_hlaseni = []

    # 4. Sjednocení hlášení do jednoho seznamu
    # Nejdříve přidáme PSY (mají fotku a jsou důležitější)
    for p in ztraceni_mazlicci:
        f_url = None
        if p.fotka:
            try:
                f_url = p.fotka.url
            except (ValueError, RuntimeError):
                f_url = None

        krizova_hlaseni.append({
            'typ': 'ztrata',
            'nazev': f"🚨 ZTRACENÝ PES: {p.jmeno}",
            'adresa': "Poslední známá poloha (GPS)",
            'foto_url': f_url,
            'objekt_id': p.id,
            'is_dog_profile': True # Pomůcka pro šablonu, abys mohl odkázat na SOS profil
        })

    # Pak přidáme ostatní hlášení z mapy (nebezpečí, návnady)
    for h in mapa_hlaseni:
        krizova_hlaseni.append({
            'typ': h.typ,
            'nazev': getattr(h, 'nazev', 'Hlášení z mapy'),
            'adresa': getattr(h, 'adresa', 'Lokalita neupřesněna'),
            'foto_url': None,
            'objekt_id': h.id,
            'is_dog_profile': False
        })

    # 5. Context pro šablonu (zobrazíme max 3 nejnovější)
    context = {
        'is_premium': is_premium,
        'krizova_hlaseni': krizova_hlaseni[:3],
    }

    return render(request, 'home/index.html', context)


@csrf_exempt
def simpleshop_webhook(request):
    print("--- WEBHOOK VOLÁN ---")
    data = request.POST

    # Získání e-mailu a názvu produktu
    email = data.get('mail_to[0]') or data.get('customer_email') or data.get('email')
    produkt = data.get('items[0][text]', '')  # Název produktu ze SimpleShopu

    print(f"DEBUG: E-mail: {email}, Produkt: {produkt}")

    if email:
        user = User.objects.filter(email__iexact=email.strip()).first()

        if user:
            profil, created = ProfilMajitele.objects.get_or_create(uzivatel=user)

            # 1. VARIANTA: Roční předplatné
            if "Roční" in produkt:
                profil.is_premium = True
                profil.premium_do = date.today() + timedelta(days=365)
                profil.save()
                print(f"DEBUG: Nastaveno ROČNÍ premium pro {email}")

            # 2. VARIANTA: Měsíční předplatné
            elif "Měsíční" in produkt or "Chovatel" in produkt:
                profil.is_premium = True
                profil.premium_do = date.today() + timedelta(days=31)
                profil.save()
                print(f"DEBUG: Nastaveno MĚSÍČNÍ premium pro {email}")

            # 3. VARIANTA: Pouze známka (neaktivuje premium)
            elif "Známka" in produkt or "nerez" in produkt:
                print(f"DEBUG: Uživatel {email} zakoupil pouze fyzickou známku.")
                # Zde můžeš přidat třeba odeslání e-mailu sobě, že máš balit balíček

            return HttpResponse("OK", status=200)

    print("DEBUG: V datech nebyl nalezen žádný e-mail nebo uživatel.")
    return HttpResponse("NO USER FOUND", status=200)


def mapa_sluzeb(request):
    # Upravený filtr: Bereme vše schválené NEBO cokoli, co je SOS (ztráta/nebezpečí)
    sluzby_queryset = Sluzba.objects.filter(
        Q(schvaleno=True) | Q(typ__in=['ztrata', 'nebezpeci'])
    )

    sluzby_data = []
    print(f"DEBUG: V tabulce Sluzba nalezeno záznamů: {sluzby_queryset.count()}")

    for s in sluzby_queryset:
        if s.lat and s.lon:
            detail_url = reverse('detail_sluzby', args=[s.id])

            if s.typ == 'ztrata':
                # Odstraníme známé předpony, které by mohly v názvu být
                ciste_jmeno = s.nazev.replace("🚨 ZTRACENÝ PES:", "").replace("🚨 HLEDÁ SE:", "").strip()

                # Hledáme psa - icontains je dobré, ale musíme dát pozor,
                # aby v 'ciste_jmeno' nebylo moc balastu
                pes = Pes.objects.filter(jmeno__icontains=ciste_jmeno).first()

                if pes:
                    detail_url = reverse('nouzovy_profil_psa', args=[pes.id])
                else:
                    # Pokud jméno obsahuje mezery (např. "Hledá se Izzabela"),
                    # zkusíme vzít jen poslední slovo jako jméno
                    posledni_slovo = s.nazev.split()[-1]
                    pes = Pes.objects.filter(jmeno__icontains=posledni_slovo).first()
                    if pes:
                        detail_url = reverse('nouzovy_profil_psa', args=[pes.id])

            sluzby_data.append({
                'id': s.id,
                'nazev': s.nazev,
                'url': detail_url,
                'typ': s.get_typ_display(),
                'typ_slug': s.typ,
                'lat': float(s.lat),
                'lon': float(s.lon),
                'adresa': s.adresa,
                'web': s.web,
                'is_ztrata': (s.typ == 'ztrata')
            })

    # 2. Kategorie pro filtry
    kategorie = []
    videno = set()
    for s in sluzby_data:
        if s['typ'] not in videno:
            kategorie.append({'nazev': s['typ'], 'slug': s['typ_slug']})
            videno.add(s['typ'])

    print(f"DEBUG: Celkem špendlíků na mapu: {len(sluzby_data)}")

    return render(request, 'home/mapa_sluzeb.html', {
        'sluzby_json': json.dumps(sluzby_data),
        'kategorie': kategorie,
        'je_prihlasen': request.user.is_authenticated
    })


@login_required
def pridat_sluzbu(request):
    if request.method == 'POST':
        form = SluzbaForm(request.POST)
        # Získání souřadnic přímo z POST dat
        lat = request.POST.get('lat')
        lon = request.POST.get('lon')

        if form.is_valid():
            # Pokud souřadnice chybí, místo chyby 500 vrátíme varování uživateli
            if not lat or not lon:
                messages.error(request, "Chyba: Nebyla vybrána poloha na mapě! Klikněte prosím do mapy.")
                return render(request, 'home/pridat_sluzbu.html', {'form': form})

            nova_sluzba = form.save(commit=False)
            nova_sluzba.vlastnik = request.user

            try:
                nova_sluzba.lat = float(str(lat).replace(',', '.'))
                nova_sluzba.lon = float(str(lon).replace(',', '.'))

                # OKAMŽITÉ ZOBRAZENÍ (bez admina) pro Nebezpečí, Ztráty a Návnady
                if nova_sluzba.typ in ['nebezpeci', 'ztrata', 'navnada']:
                    nova_sluzba.schvaleno = True
                else:
                    nova_sluzba.schvaleno = False

                nova_sluzba.save()
                messages.success(request, "Hlášení bylo úspěšně zveřejněno!")
                return redirect('mapa_sluzeb')
            except ValueError:
                messages.error(request, "Chyba: Neplatný formát souřadnic.")
    else:
        form = SluzbaForm()
    return render(request, 'home/pridat_sluzbu.html', {'form': form})


@login_required
def smazat_sluzbu(request, pk):
    """Smaže záznam bez nutnosti potvrzovací šablony (oprava chyby TemplateDoesNotExist)."""
    sluzba = get_object_or_404(Sluzba, pk=pk, vlastnik=request.user)
    # Mažeme rovnou, pokud uživatel klikne na odkaz (nebo přes POST)
    sluzba.delete()
    messages.success(request, "Záznam byl úspěšně odstraněn.")
    return redirect('mapa_sluzeb')

def stale_aktualni(request, id):
    from django.utils import timezone
    from django.http import JsonResponse
    sluzba = get_object_or_404(Sluzba, id=id)
    sluzba.vytvoreno = timezone.now()
    sluzba.save()
    return JsonResponse({'status': 'ok'})


def nahlasit_neaktualni(request, id):
    """Komunitní mazání: Nebezpečí zmizí po 3 hlasech."""
    sluzba = get_object_or_404(Sluzba, id=id)
    sluzba.potvrzeni_minus += 1

    # Kontrola pro kategorii NEBEZPEČÍ
    if sluzba.typ == 'nebezpeci' and sluzba.potvrzeni_minus >= 3:
        sluzba.delete()
        return JsonResponse({'status': 'deleted', 'message': 'Nebezpečí bylo odstraněno z mapy.'})

    sluzba.save()
    return JsonResponse({'status': 'ok', 'count': sluzba.potvrzeni_minus})


@login_required
def upravit_sluzbu(request, pk):
    sluzba = get_object_or_404(Sluzba, pk=pk, vlastnik=request.user)
    if request.method == 'POST':
        form = SluzbaForm(request.POST, instance=sluzba)
        if form.is_valid():
            upravena = form.save(commit=False)

            # SOS kategorie (ztráta/nebezpečí) jsou vždy schválené hned
            if upravena.typ in ['ztrata', 'nebezpeci']:
                upravena.schvaleno = True
                messages.success(request, "SOS hlášení bylo aktualizováno.")
            else:
                upravena.schvaleno = False
                messages.info(request, "Změny uloženy a čekají na schválení administrátorem.")

            upravena.save()
            return redirect('mapa_sluzeb')
    else:
        form = SluzbaForm(instance=sluzba)
    # Použijeme tvou existující šablonu pro přidání
    return render(request, 'home/pridat_sluzbu.html', {'form': form, 'editace': True})


def detail_sluzby(request, pk):
    sluzba = get_object_or_404(Sluzba, pk=pk)
    # Tady se volají ty funkce Avg a Count, které musíme nahoře importovat
    stats = sluzba.recenze_set.aggregate(
        prumer=Avg('hvezdy'),
        pocet=Count('id')
    )

    return render(request, 'home/detail_sluzby.html', {
        'sluzba': sluzba,
        'prumer': stats['prumer'],
        'pocet_recenzi': stats['pocet']
    })


@login_required
def pridat_recenzi(request, pk):
    # Importy uvnitř funkce jsou fajn, ale raději je měj nahoře v souboru
    from users.models import Notifikace
    from .models import Sluzba
    from .forms import RecenzeForm  # <--- Ujisti se, že importuješ správný FORM!

    sluzba_obj = get_object_or_404(Sluzba, pk=pk)

    if request.method == 'POST':
        # TENTO ŘÁDEK TI TAM CHYBĚL (proto bylo 'form' podtržené):
        form = RecenzeForm(request.POST)

        if form.is_valid():
            nova_recenze = form.save(commit=False)
            # Tady pozor: v modelu Recenze se to pole jmenuje 'vhome' nebo 'sluzba'?
            # Podle tvého kódu předpokládám 'vhome'
            nova_recenze.vhome = sluzba_obj
            nova_recenze.user = request.user
            nova_recenze.save()

            # Vytvoření notifikace pro majitele
            if sluzba_obj.user != request.user:
                Notifikace.objects.create(
                    prijemce=sluzba_obj.user,
                    odesilatel=request.user,
                    typ='recenze',
                    text=f"napsal hodnocení k vaší službě {sluzba_obj.nazev}",
                    sluzba=sluzba_obj,
                    precteno=False
                )
            return redirect('detail_sluzby', pk=pk)
    else:
        # Tohle se stane, když uživatel na stránku jen přijde (GET)
        form = RecenzeForm()

    # Musíš funkci zakončit renderem, jinak ti to hodí chybu, pokud form nebude validní
    return render(request, 'vhome/detail_sluzby.html', {'form': form, 'sluzba': sluzba_obj})


def kontakt(request):
    if request.method == 'POST':
        form = KontaktForm(request.POST)
        if form.is_valid():
            # Tady by se odesílal mail, zatím jen vrátíme úspěch
            return render(request, 'home/kontakt.html', {'success': True})
    else:
        form = KontaktForm()
    return render(request, 'home/kontakt.html', {'form': form})


def podminky(request):
    moje_info = {
        'jmeno': 'Ivana Elšíková',
        'ico': '23834838',
        'adresa': 'Sokolská 29, Hvozdná, 76310',
    }

    # KONTROLA: Pokud už uživatel souhlasil dříve, nepouštěj ho k potvrzovacímu tlačítku
    if request.user.is_authenticated and hasattr(request.user, 'profil'):
        if request.user.profil.souhlas_podminky:
            # Možnost A: Přesměruj ho pryč, už tu nemá co potvrozovat
            # return redirect('home')

            # Možnost B: Zobraz mu stránku, ale v šabloně skryjeme tlačítko (lepší pro info)
            return render(request, 'home/podminky.html', {
                'kontaktni_info': moje_info,
                'uz_souhlasil': True
            })

    if request.method == 'POST' and request.user.is_authenticated:
        if hasattr(request.user, 'profil'):
            profil = request.user.profil
            profil.souhlas_podminky = True
            profil.save()
            return redirect('profil')
        else:
            return redirect('home')

    return render(request, 'home/podminky.html', {'kontaktni_info': moje_info, 'uz_souhlasil': False})


def gdpr(request):
    context = {
        'kontaktni_info': {
            'jmeno': 'Ivana Elšíková',
            'ico': '23834838',
            'adresa': 'Sokolská 29, Hvozdná, 763 10',
            'email': 'elivdruhy@gmail.com',
        }
    }
    return render(request, 'home/gdpr.html', context)

def cookies(request):
    return render(request, 'home/cookies.html')

def cenik(request):
    mazlicek = None
    if request.user.is_authenticated:
        # 1. Získáme profil (pokud existuje)
        if hasattr(request.user, 'profilmajitele'):
            profil = request.user.profilmajitele
            # 2. Najdeme prvního psa tohoto profilu
            mazlicek = Pes.objects.filter(majitel=profil).first()

    # TENTO ŘÁDEK MUSÍ BÝT ÚPLNĚ VLEVO (mimo ty if-podmínky)
    # Aby se stránka zobrazila i nepřihlášeným lidem
    return render(request, 'home/cenik.html', {'mazlicek': mazlicek})


def dekujeme_za_nakup(request):
    """Zobrazí stránku po úspěšné platbě."""
    return render(request, 'home/dekujeme.html')

def dekujeme_za_znamku(request):
    return render(request, 'home/dekujeme_za_znamku.html')

def pruvodce(request):
    return render(request, 'home/pruvodce.html')
