import json
from datetime import timedelta, date
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages

# Importy tvých modelů a forem
from .models import Sluzba, KontaktniZprava
from .forms import SluzbaForm, KontaktForm
from users.models import Prispevek, Pes, ProfilMajitele
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import HttpResponse
from django.contrib.auth.models import User
from datetime import date, timedelta
from django.shortcuts import render

# --- 1. HLAVNÍ STRÁNKA (OPRAVENÁ) ---
def index(request):
    is_premium = False

    if request.user.is_authenticated:
        profil = ProfilMajitele.objects.filter(uzivatel=request.user).first()
        if profil:
            if profil.is_premium:
                if profil.premium_do:
                    is_premium = profil.premium_do >= date.today()
                else:
                    is_premium = True
            else:
                is_premium = False

    # Načtení dat pro šablonu (ztracení psi a zeď)
    ztraceni_psi = Pes.objects.filter(je_ztraceny=True)
    posledni_prispevky = Prispevek.objects.all().order_by('-datum_pridani')[:5] # Načte posledních 5 příspěvků

    return render(request, 'home/index.html', {
        'je_premium': is_premium,
        'ztraceni_psi': ztraceni_psi,
        'posledni_prispevky': posledni_prispevky,
    })

@csrf_exempt
def simpleshop_webhook(request):
    """Webhook pro zpracování plateb ze Simpleshopu."""
    if request.method == 'POST':
        try:
            # 1. Načtení dat ze Simpleshopu
            try:
                data = json.loads(request.body)
                email = data.get('customer', {}).get('email')
                event = data.get('event')
                product_id = data.get('product', {}).get('id')
            except:
                email = request.POST.get('customer_email') or request.POST.get('email')
                event = request.POST.get('event')
                product_id = request.POST.get('product_id')

            # 2. Zpracování úspěšné platby
            if event == 'invoice.paid' and email:
                try:
                    user = User.objects.get(email=email)
                    profil = user.profil  # Předpokládám, že máš profil přes related_name='profil'

                    # 3. ROZLIŠENÍ PLÁNŮ PODLE ID PRODUKTU
                    # --- TADY ZMĚŇ ID NA TVOJE SKUTEČNÁ ID ZE SIMPLESHOPU ---
                    if product_id == '142677':
                        profil.is_premium = True
                        profil.premium_do = date.today() + timedelta(days=30)  # Příklad 30 dní
                        print(f"✅ Aktivován Chovatel pro: {email}")

                    elif product_id == '142680':
                        profil.is_premium = True
                        profil.premium_do = date.today() + timedelta(days=365)
                        print(f"✅ Aktivován Profi pro: {email}")

                    profil.save()
                    return HttpResponse("OK", status=200)

                except User.DoesNotExist:
                    print(f"⚠️ Uživatel s e-mailem {email} nenalezen.")
                    return HttpResponse("User not found", status=404)

            return HttpResponse("Event ignored", status=200)

        except Exception as e:
            print(f"⚠️ Chyba Webhooku: {e}")
            return HttpResponse("Error", status=500)

    return HttpResponse("Method not allowed", status=405)

@login_required
def dekujeme_za_nakup(request):
    """Stránka po úspěšném nákupu."""
    return render(request, 'home/dekujeme.html')


# --- 3. MAPA SLUŽEB ---
def mapa_sluzeb(request):
    # 1. FYZICKÉ SMAZÁNÍ (Pojistka pro čistou databázi)
    # Smažeme nebezpečí starší než 7 dní (necháme je tam o kousek déle pro jistotu)
    limit_smazani = timezone.now() - timedelta(days=7)
    Sluzba.objects.filter(typ='nebezpeci', vytvoreno__lt=limit_smazani).delete()

    # 2. FILTR PRO ZOBRAZENÍ (To, co uvidí uživatel na mapě)
    # Definujeme hranici 3 dny pro zobrazení výstrahy
    limit_vystrahy = timezone.now() - timedelta(days=3)

    # Vybereme služby, které jsou schválené...
    # ...A u nebezpečí přidáme podmínku, že nesmí být starší než 3 dny
    sluzby_queryset = Sluzba.objects.filter(
        Q(schvaleno=True) |
        Q(typ='nebezpeci', vytvoreno__gte=limit_vystrahy)
    )

    sluzby_data = []
    for s in sluzby_queryset:
        # Pokud má služba moc nahlášení (potvrzeni_minus >= 3), přeskočíme ji
        if s.typ == 'nebezpeci' and s.potvrzeni_minus >= 3:
            continue

        try:
            lat, lon = float(s.lat), float(s.lon)
            if lon > 180: lon = lon / 1000000
        except:
            lat, lon = 0, 0

        sluzby_data.append({
            'id': s.id,
            'nazev': s.nazev,
            'typ': s.get_typ_display(),
            'typ_slug': s.typ,
            'lat': lat,
            'lon': lon,
            'adresa': s.adresa,
            'telefon': s.telefon,
            'popis': s.popis,
            'web': s.web,
        })

    context = {
        'sluzby_json': json.dumps(sluzby_data),
        'je_prihlasen': request.user.is_authenticated
    }
    # Opravený return, aby používal context
    return render(request, 'home/mapa_sluzeb.html', context)


@login_required
def pridat_sluzbu(request):
    if request.method == 'POST':
        form = SluzbaForm(request.POST)
        if form.is_valid():
            nova_sluzba = form.save(commit=False)
            nova_sluzba.vlastnik = request.user
            if nova_sluzba.typ == 'nebezpeci':
                nova_sluzba.schvaleno = True
            nova_sluzba.save()
            messages.success(request, "Záznam byl odeslán ke schválení. Po prověření administrátorem se objeví na mapě.")
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
            form.save()
            messages.info(request, "Změny byly uloženy.")
            return redirect('mapa_sluzeb')
    else:
        form = SluzbaForm(instance=sluzba)
    return render(request, 'home/pridat_sluzbu.html', {'form': form, 'editace': True})


@login_required
def smazat_sluzbu(request, pk):
    sluzba = get_object_or_404(Sluzba, pk=pk, vlastnik=request.user)
    if request.method == 'POST':
        sluzba.delete()
        messages.success(request, "Záznam byl odstraněn.")
        return redirect('mapa_sluzeb')
    return render(request, 'home/smazat_confirm.html', {'sluzba': sluzba})


# --- 4. KOMUNITNÍ FUNKCE ---
def nahlasit_neaktualni(request, id):
    sluzba = get_object_or_404(Sluzba, id=id)
    sluzba.potvrzeni_minus += 1
    sluzba.save()
    if sluzba.typ == 'nebezpeci' and sluzba.potvrzeni_minus >= 3:
        sluzba.delete()
        return JsonResponse({'status': 'deleted'})
    return JsonResponse({'status': 'ok'})


def stale_aktualni(request, id):
    sluzba = get_object_or_404(Sluzba, id=id)
    sluzba.vytvoreno = timezone.now()
    sluzba.save()
    return JsonResponse({'status': 'ok'})


# --- 5. OSTATNÍ ---
def kontakt(request):
    if request.method == 'POST':
        form = KontaktForm(request.POST)
        if form.is_valid():
            # Tady můžeš přidat odeslání mailu
            return render(request, 'home/kontakt.html', {'success': True})
    return render(request, 'home/kontakt.html', {'form': KontaktForm()})


def podminky(request):
    # --- TADY NASTAV SVOJE INFORMACE ---
    moje_info = {
        'jmeno': 'Ivana Elšíková',  # Tvoje jméno nebo název firmy
        'ico': '23834838',          # Tvoje IČO
        'adresa': 'Sokolská 29, Hvozdná, 76310', # Tvoje adresa
    }
    # ------------------------------------
    return render(request, 'home/podminky.html', {'kontaktni_info': moje_info})

def gdpr(request):
    """
    Zobrazí stránku se zásadami ochrany osobních údajů.
    """
    context = {
        'kontaktni_info': {
            'jmeno': 'Ivana Elšíková',
            'ico': '23834838',
            'adresa': 'Sokolská 29, Hvozdná, 763 10',
            'email': 'elivdruhy@gmail.com',
        }
    }
    return render(request, 'home/gdpr.html', context)



def cookies(request): return render(request, 'home/cookies.html')


def cenik(request): return render(request, 'home/cenik.html')
