import json
from datetime import timedelta, date
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
import json
from datetime import date
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User

# Importy tvých modelů a forem
from .models import Sluzba, KontaktniZprava
from .forms import SluzbaForm, KontaktForm
from users.models import Prispevek, Pes, ProfilMajitele

def index(request):
    # 1. Zabezpečení proti chybám v Premium (pokud model neexistuje)
    is_premium = False
    try:
        if request.user.is_authenticated and hasattr(request.user, 'profilmajitele'):
            profil = request.user.profilmajitele
            is_premium = profil.is_premium and (not profil.premium_do or profil.premium_do >= date.today())
    except Exception:
        is_premium = False

    # 2. Načtení dat z mapy
    limit_cas = timezone.now() - timedelta(days=7)
    try:
        mapa_hlaseni = Sluzba.objects.filter(
            typ__in=['nebezpeci', 'ztrata'],
            vytvoreno__gte=limit_cas
        )
    except Exception:
        mapa_hlaseni = []

    # 3. Načtení ztracených psů
    try:
        ztraceni_mazlicci = Pes.objects.filter(je_ztraceny=True)
    except Exception:
        ztraceni_mazlicci = []

    krizova_hlaseni = []

    # 4. Sjednocení hlášení (Klíčové pro šablonu!)
    for h in mapa_hlaseni:
        krizova_hlaseni.append({
            'typ': h.typ,
            'nazev': getattr(h, 'nazev', 'Hlášení z mapy'),
            'adresa': getattr(h, 'adresa', 'Lokalita neupřesněna'),
            'foto_url': None,
            'objekt_id': h.id
        })

    for p in ztraceni_mazlicci:
        # TADY JE TA NEJČASTĚJŠÍ CHYBA:
        # Pokud soubor v media/users neexistuje, p.fotka.url vyhodí chybu.
        f_url = None
        if p.fotka:
            try:
                f_url = p.fotka.url
            except (ValueError, RuntimeError):
                f_url = None  # Pokud soubor chybí na disku, prostě url nedáme

        krizova_hlaseni.append({
            'typ': 'ztrata',
            'nazev': f"HLEDÁ SE: {p.jmeno}",
            'adresa': "Poslední výskyt u majitele",
            'foto_url': f_url,
            'objekt_id': p.id
        })

    # 5. Context pro šablonu
    context = {
        'is_premium': is_premium,
        'krizova_hlaseni': krizova_hlaseni[:3],
    }

    return render(request, 'home/index.html', context)


@csrf_exempt
def simpleshop_webhook(request):
    print("--- WEBHOOK VOLÁN ---")
    data = request.POST

    # SimpleShop posílá email v poli mail_to[0] nebo customer_email
    email = data.get('mail_to[0]') or data.get('customer_email') or data.get('email')

    # DEBUG hláška pro tebe do logu
    print(f"DEBUG: Zkouším aktivovat e-mail: {email}")

    if email:
        # Hledáme uživatele v databázi
        user = User.objects.filter(email__iexact=email.strip()).first()

        if user:
            profil, created = ProfilMajitele.objects.get_or_create(uzivatel=user)
            profil.is_premium = True

            # Zjistíme, co si koupil (v logu jsme viděli 'Roční Profi')
            produkt = data.get('items[0][text]', '')

            if "Roční" in produkt:
                profil.premium_do = date.today() + timedelta(days=365)
                print(f"DEBUG: Nastaveno ROČNÍ premium pro {email}")
            else:
                # Defaultně měsíc pro ostatní (Chovatel)
                profil.premium_do = date.today() + timedelta(days=31)
                print(f"DEBUG: Nastaveno MĚSÍČNÍ premium pro {email}")

            profil.save()

    print("DEBUG: V datech nebyl nalezen žádný e-mail.")
    return HttpResponse("NO EMAIL PROVIDED", status=200)

def mapa_sluzeb(request):
    # 1. Načtení schválených služeb
    sluzby_queryset = Sluzba.objects.filter(schvaleno=True)
    sluzby_data = []

    for s in sluzby_queryset:
        if s.lat and s.lon:
            sluzby_data.append({
                'id': s.id,
                'nazev': s.nazev,
                'typ': s.get_typ_display(),
                'typ_slug': s.typ,
                'lat': float(s.lat),
                'lon': float(s.lon),
                'adresa': s.adresa,
                'url': f"/detail-sluzby/{s.id}/",
                'web': s.web,
                'is_ztrata': False
            })

    # 2. Ztracení psi
    ztraceni_psi = Pes.objects.filter(je_ztraceny=True)

    # --- TENTO PRINT TEĎ UŽ UVIDÍŠ V TERMINÁLU ---
    print(f"DEBUG: V databázi nalezeno ztracených psů: {ztraceni_psi.count()}")

    for p in ztraceni_psi:
        # Pustíme psa dál, pokud pole nejsou None
        if p.lat is not None and p.lon is not None:
            try:
                # POZOR: Musí se to jmenovat 'detail_psa', jak máš v urls.py
                pes_url = reverse('detail_psa', args=[p.id])

                sluzby_data.append({
                    'id': p.id,
                    'nazev': f"🚨 HLEDÁ SE: {p.jmeno}",
                    'typ': "ZTRACENÝ MAZLÍČEK",
                    'typ_slug': 'ztrata',
                    'lat': float(p.lat),
                    'lon': float(p.lon),
                    'adresa': getattr(p, 'posledni_vyskyt', "Poloha neupřesněna"),
                    'url': pes_url,
                    'is_ztrata': True
                })
                print(f"DEBUG: Pes {p.jmeno} úspěšně přidán do seznamu.")
            except Exception as e:
                print(f"DEBUG: Chyba u psa {p.jmeno}: {e}")
        else:
            print(f"DEBUG: Pes {p.jmeno} je ztracený, ale NEMÁ SOUŘADNICE v DB!")

    # 3. Kategorie pro filtry
    kategorie = []
    videno = set()
    for s in sluzby_data:
        if s['typ'] not in videno:
            kategorie.append({'nazev': s['typ'], 'slug': s['typ_slug']})
            videno.add(s['typ'])

    print(f"DEBUG: Celkem objektů na mapu: {len(sluzby_data)}")

    return render(request, 'home/mapa_sluzeb.html', {
        'sluzby_json': json.dumps(sluzby_data),
        'kategorie': kategorie,
        'je_prihlasen': request.user.is_authenticated
    })

def detail_sluzby(request, pk):
    sluzba = get_object_or_404(Sluzba, pk=pk)
    return render(request, 'home/detail_sluzby.html', {'sluzba': sluzba})

@login_required
def pridat_sluzbu(request):
    """Tato funkce umožní lidem přidat novou službu."""
    if request.method == 'POST':
        form = SluzbaForm(request.POST)
        if form.is_valid():
            nova_sluzba = form.save(commit=False)
            nova_sluzba.vlastnik = request.user
            # Pokud je to nebezpečí, schválíme hned, jinak čeká na admina
            nova_sluzba.schvaleno = (nova_sluzba.typ == 'nebezpeci')
            nova_sluzba.save()
            messages.success(request, "Záznam byl uložen.")
            return redirect('mapa_sluzeb')
    else:
        form = SluzbaForm()
    return render(request, 'home/pridat_sluzbu.html', {'form': form})


@login_required
def upravit_sluzbu(request, pk):
    sluzba = get_object_or_404(Sluzba, pk=pk, vlastnik=request.user)
    if request.method == 'POST':
        form = SluzbaForm(request.POST, instance=sluzba)
        if form.is_valid():
            upravena = form.save(commit=False)

            # LOGIKA SCHVALOVÁNÍ:
            # Pokud je to nebezpečí nebo ztráta, necháme 'schvaleno' jak je (nebo True).
            # Ostatní (salony, veteriny) při změně raději shodíme do False pro kontrolu.
            if upravena.typ not in ['nebezpeci', 'ztrata']:
                upravena.schvaleno = False
                messages.info(request, "Změny uloženy a čekají na schválení.")
            else:
                messages.success(request, "Záznam byl okamžitě aktualizován.")

            upravena.save()
            return redirect('mapa_sluzeb')
    else:
        form = SluzbaForm(instance=sluzba)
    return render(request, 'home/pridat_sluzbu.html', {'form': form, 'editace': True})

@login_required
def smazat_sluzbu(request, pk):
    """Tato funkce umožní majiteli smazat jeho záznam z mapy."""
    sluzba = get_object_or_404(Sluzba, pk=pk, vlastnik=request.user)
    if request.method == 'POST':
        sluzba.delete()
        messages.success(request, "Záznam byl úspěšně odstraněn.")
        return redirect('mapa_sluzeb')
    # Pokud uživatel jen klikne na smazat, ukážeme mu potvrzovací stránku
    return render(request, 'home/smazat_confirm.html', {'sluzba': sluzba})


def nahlasit_neaktualni(request, id):
    """Služba dostane 'mínus bod'. U nebezpečí se po 3 nahlášeních smaže."""
    sluzba = get_object_or_404(Sluzba, id=id)
    sluzba.potvrzeni_minus += 1
    sluzba.save()

    # Pokud je to nebezpečí a má 3 a více nahlášení, hned ho smažeme
    if sluzba.typ == 'nebezpeci' and sluzba.potvrzeni_minus >= 3:
        sluzba.delete()
        return JsonResponse({'status': 'deleted'})

    return JsonResponse({'status': 'ok'})


def stale_aktualni(request, id):
    """Pokud někdo potvrdí, že to tam pořád je, obnovíme čas vytvoření."""
    sluzba = get_object_or_404(Sluzba, id=id)
    sluzba.vytvoreno = timezone.now()
    sluzba.save()
    return JsonResponse({'status': 'ok'})

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
    return render(request, 'home/podminky.html', {'kontaktni_info': moje_info})

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
    return render(request, 'home/cenik.html')

def dekujeme_za_nakup(request):
    """Zobrazí stránku po úspěšné platbě."""
    return render(request, 'home/dekujeme.html')

