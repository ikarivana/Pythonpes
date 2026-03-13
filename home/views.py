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

# Importy tvých modelů a forem
from .models import Sluzba, KontaktniZprava
from .forms import SluzbaForm, KontaktForm
from users.models import Prispevek, Pes, ProfilMajitele


# --- 1. HLAVNÍ STRÁNKA ---
def index(request):
    is_premium = False
    if request.user.is_authenticated:
        # Používáme hasattr pro bezpečné ověření existence profilu
        if hasattr(request.user, 'profilmajitele'):
            profil = request.user.profilmajitele
            is_premium = profil.is_premium and (not profil.premium_do or profil.premium_do >= date.today())

    context = {
        'je_premium': is_premium,
        'ztraceni_psi': Pes.objects.filter(je_ztraceny=True),
        'posledni_prispevky': Prispevek.objects.all().order_by('-datum_pridani')[:5],
    }
    return render(request, 'home/index.html', context)


# --- 2. PLATEBNÍ SYSTÉM (SIMPLESHOP) ---
@csrf_exempt
def simpleshop_webhook(request):
    """Zpracování plateb ze Simpleshopu."""
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)

    try:
        # Sjednocení načítání dat (JSON i POST)
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        # Simpleshop posílá data v hluboké struktuře nebo napřímo
        email = data.get('customer', {}).get('email') if isinstance(data.get('customer'), dict) else data.get(
            'customer_email')
        event = data.get('event')
        product_id = str(data.get('product', {}).get('id')) if isinstance(data.get('product'), dict) else str(
            data.get('product_id'))

        if event == 'invoice.paid' and email:
            user = User.objects.filter(email__iexact=email).first()
            if user:
                # Získáme nebo vytvoříme profil
                profil, created = ProfilMajitele.objects.get_or_create(uzivatel=user)

                # Rozlišení tarifů
                dni_pridat = 30 if product_id == '142677' else 365 if product_id == '142680' else 0

                if dni_pridat > 0:
                    profil.is_premium = True
                    # Pokud již premium má, přičteme k datu, jinak od dneška
                    start_date = max(profil.premium_do or date.today(), date.today())
                    profil.premium_do = start_date + timedelta(days=dni_pridat)
                    profil.save()
                    return HttpResponse(f"✅ Premium aktivováno na {dni_pridat} dní", status=200)

            return HttpResponse("User not found", status=404)

        return HttpResponse("Ignored event", status=200)

    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)


def mapa_sluzeb(request):
    # 1. Načtení schválených služeb
    sluzby_queryset = Sluzba.objects.filter(schvaleno=True)
    sluzby_data = []

    for s in sluzby_queryset:
        if s.lat and s.lon:
            sluzby_data.append({
                'id': s.id,
                'nazev': s.nazev,
                'typ': s.get_typ_display(), # Tohle je ten hezký název s ikonou pro popup
                'typ_slug': s.typ,
                'lat': float(s.lat),
                'lon': float(s.lon),
                'adresa': s.adresa,
                'url': f"/detail-sluzby/{s.id}/", # Uprav podle potřeby
                'is_ztrata': False
            })

    # 2. Ztracení psi
    ztraceni_psi = Pes.objects.filter(je_ztraceny=True)
    for p in ztraceni_psi:
        if p.lat and p.lon:
            sluzby_data.append({
                'id': p.id,
                'nazev': f"🚨 HLEDÁ SE: {p.jmeno}",
                'typ': "ZTRACENÝ MAZLÍČEK",
                'typ_slug': 'ztrata', # Speciální slug pro SOS barvu
                'lat': float(p.lat),
                'lon': float(p.lon),
                'adresa': getattr(p, 'posledni_vyskyt', "Poloha neupřesněna"),
                'url': reverse('nouzovy_profil_psa', args=[p.id]),
                'is_ztrata': True
            })

    # 3. Kategorie pro filtry (automaticky ze seznamu)
    kategorie = []
    videno = set()
    for s in sluzby_data:
        if s['typ'] not in videno:
            kategorie.append({'nazev': s['typ'], 'slug': s['typ_slug']})
            videno.add(s['typ'])

    # POZOR NA ODSZENÍ - return musí být až úplně na konci funkce
    return render(request, 'home/mapa_sluzeb.html', {
        'sluzby_json': json.dumps(sluzby_data),
        'kategorie': kategorie,
        'je_prihlasen': request.user.is_authenticated
    })

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
    """Tato funkce umožní vlastnikovi změnit údaje u jeho služby."""
    sluzba = get_object_or_404(Sluzba, pk=pk, vlastnik=request.user)
    if request.method == 'POST':
        form = SluzbaForm(request.POST, instance=sluzba)
        if form.is_valid():
            form.save()
            messages.info(request, "Změny byly uloženy.")
            return redirect('mapa_sluzeb')
    else:
        # Tady pošleme do formuláře stávající data služby
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

@csrf_exempt
def simpleshop_webhook(request):
    """Tady se zpracovávají automatické platby (webhook)."""
    # Pokud zatím nemáš logiku, necháme tu jen základ:
    return HttpResponse("OK", status=200)