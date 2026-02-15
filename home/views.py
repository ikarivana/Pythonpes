import json
from datetime import timedelta, date

from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt

# Importy tvých modelů a forem
from .models import Sluzba, KontaktniZprava
from .forms import SluzbaForm, KontaktForm
from inzerce.models import Inzerat, InzeratFoto
from inzerce.forms import InzeratForm
from users.models import Plemeno, Prispevek, Pes, ProfilMajitele

# --- 1. HLAVNÍ STRÁNKA (OPRAVENÁ) ---
def index(request):
    je_premium = False
    if request.user.is_authenticated:
        # Vynutíme si čerstvé data z databáze
        profil = ProfilMajitele.objects.filter(uzivatel=request.user).first()
        if profil:
            je_premium = profil.is_premium

    # --- PŘIDÁNO: Načtení ztracených psů ---
    ztraceni_psi = Pes.objects.filter(je_ztraceny=True)

    return render(request, 'home/index.html', {
        'je_premium': je_premium,
        'ztraceni_psi': ztraceni_psi,  # Posíláme seznam ztracených psů do šablony
    })


@csrf_exempt
def simpleshop_webhook(request):
    """
    Tato funkce čeká na 'pípnutí' ze SimpleShopu.
    """
    if request.method == 'POST':
        try:
            # SimpleShop posílá data o objednávce
            data = json.loads(request.body)

            # 1. Získáme e-mail zákazníka a typ události
            email = data.get('customer', {}).get('email')
            event = data.get('event')  # Očekáváme 'invoice.paid'

            # Pokud je faktura zaplacená, jdeme do akce
            if event == 'invoice.paid' and email:
                try:
                    # Najdeme uživatele podle e-mailu
                    user = User.objects.get(email=email)

                    # Máš v modelu: related_name='profil'
                    profil = user.profil

                    # AKTIVACE PREMIUM
                    profil.je_premium = True
                    # Nastavíme platnost na 1 rok
                    profil.premium_do = date.today() + timedelta(days=365)
                    profil.save()

                    print(f"Úspěch: Uživatel {email} je nyní ALFA!")
                    return HttpResponse(status=200)

                except User.DoesNotExist:
                    print(f"Webhook: E-mail {email} u nás nemá účet.")
                    # Vrátíme 200, aby SimpleShop neházel chybu,
                    # ale v logu to uvidíme.
                    return HttpResponse(status=200)

        except Exception as e:
            print(f"Chyba Webhooku: {e}")
            return HttpResponse(status=400)

    return HttpResponse("Metoda není povolena", status=405)


# --- 2. BAZAR (INZERCE) ---
def seznam_inzeratu(request):
    kraj_filtr = request.GET.get('kraj')
    typ_filtr = request.GET.get('typ')
    inzeraty = Inzerat.objects.all().order_by('-vytvoreno')

    if kraj_filtr:
        inzeraty = inzeraty.filter(kraj=kraj_filtr)
    if typ_filtr:
        inzeraty = inzeraty.filter(pohlavi=typ_filtr)

    context = {
        'inzeraty': inzeraty,
        'kraje': Inzerat.KRAJE_CHOICES,
    }
    return render(request, 'inzerce/seznam_inzeratu.html', context)


def detail_inzeratu(request, pk):
    inzerat = get_object_or_404(Inzerat, pk=pk)
    galerie = InzeratFoto.objects.filter(inzerat=inzerat)
    return render(request, 'inzerce/detail_inzeratu.html', {
        'inzerat': inzerat,
        'galerie': galerie
    })


@login_required
def pridat_inzerat(request):
    if request.method == 'POST':
        form = InzeratForm(request.POST, request.FILES)
        if form.is_valid():
            novy_inzerat = form.save(commit=False)
            novy_inzerat.autor = request.user
            novy_inzerat.save()

            extra_fotky = request.FILES.getlist('galerie_fotky')
            for f in extra_fotky:
                InzeratFoto.objects.create(inzerat=novy_inzerat, foto=f)

            messages.success(request, "Inzerát byl úspěšně přidán.")
            return redirect('seznam_inzeratu')
    else:
        form = InzeratForm()
    return render(request, 'inzerce/pridat_inzerat.html', {'form': form})


@login_required
def upravit_inzerat(request, pk):
    inzerat = get_object_or_404(Inzerat, pk=pk, autor=request.user)
    if request.method == 'POST':
        form = InzeratForm(request.POST, request.FILES, instance=inzerat)
        if form.is_valid():
            form.save()
            messages.success(request, "Inzerát byl upraven.")
            return redirect('detail_inzeratu', pk=inzerat.pk)
    else:
        form = InzeratForm(instance=inzerat)
    return render(request, 'inzerce/pridat_inzerat.html', {'form': form, 'editace': True})


@login_required
def smazat_inzerat(request, pk):
    inzerat = get_object_or_404(Inzerat, pk=pk, autor=request.user)
    if request.method == 'POST':
        inzerat.delete()
        messages.success(request, "Inzerát byl smazán.")
        return redirect('seznam_inzeratu')
    return render(request, 'inzerce/smazat_confirm.html', {'inzerat': inzerat})


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
        })

    context = {
        'sluzby_json': json.dumps(sluzby_data),
        'je_prihlasen': request.user.is_authenticated  # Pro snadnou kontrolu v šabloně
    }
    return render(request, 'home/mapa_sluzeb.html', {'sluzby_json': json.dumps(sluzby_data)})

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


def podminky(request): return render(request, 'home/podminky.html')


def cookies(request): return render(request, 'home/cookies.html')


def cenik(request): return render(request, 'home/cenik.html')

