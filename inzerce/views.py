from django.contrib.auth.decorators import login_required
from django.contrib import messages  # Opravený import
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Case, When, BooleanField

from .forms import InzeratForm
from .models import Inzerat, InzeratFoto


# 1. HLAVNÍ PŘEHLED INZERÁTŮ
def seznam_inzeratu(request):
    """
    Zobrazení přehledu inzerátů.
    Prémioví uživatelé (ALFA) jsou vždy nahoře, následně podle data.
    """
    kraj_filtr = request.GET.get('kraj')
    kategorie_filtr = request.GET.get('kategorie')
    hledat = request.GET.get('q')

    # QuerySet s anotací pro efektivní řazení v DB
    inzeraty = Inzerat.objects.all().select_related('autor__profil', 'autor').annotate(
        je_premium=Case(
            When(autor__profil__is_premium=True, then=True),
            default=False,
            output_field=BooleanField(),
        )
    ).filter(aktivni=True)

    # Filtrování
    if kraj_filtr:
        inzeraty = inzeraty.filter(kraj=kraj_filtr)
    if kategorie_filtr:
        inzeraty = inzeraty.filter(kategorie=kategorie_filtr)
    if hledat:
        inzeraty = inzeraty.filter(titulek__icontains=hledat) | inzeraty.filter(text__icontains=hledat)

    # Finální řazení: Premium první, pak nejnovější
    inzeraty = inzeraty.order_by('-je_premium', '-vytvoreno')

    context = {
        'inzeraty': inzeraty,
        'kraje': Inzerat.KRAJE_CHOICES,
        'kategorie_list': Inzerat.KATEGORIE_CHOICES,  # Sjednocený název pro šablonu
        'aktivni_kraj': kraj_filtr,
        'aktivni_kat': kategorie_filtr,
    }
    return render(request, 'inzerce/seznam_inzeratu.html', context)


# 2. DETAIL INZERÁTU
def detail_inzeratu(request, pk):
    """Zobrazení detailu jednoho inzerátu s galerií."""
    inzerat = get_object_or_404(Inzerat, pk=pk)
    galerie = inzerat.galerie.all()

    context = {
        'inzerat': inzerat,
        'galerie': galerie,
    }
    return render(request, 'inzerce/detail_inzeratu.html', context)


# 3. PŘIDÁNÍ INZERÁTU (S kontrolou limitu)
@login_required
def pridat_inzerat(request):
    """Přidání inzerátu: Běžný uživatel max 1 aktivní, ALFA člen neomezeně."""

    # Bezpečné získání profilu a kontrola limitu
    profil = getattr(request.user, 'profil', None)
    is_premium = profil.is_premium if profil else False
    pocet_aktivnich = Inzerat.objects.filter(autor=request.user, aktivni=True).count()

    if not is_premium and pocet_aktivnich >= 1:
        messages.warning(request,
                         "Jako běžný uživatel můžete mít pouze 1 aktivní inzerát. Pro neomezené vkládání aktivujte Členství ALFA.")
        return redirect('cenik')

    if request.method == 'POST':
        form = InzeratForm(request.POST, request.FILES)
        if form.is_valid():
            novy_inzerat = form.save(commit=False)
            novy_inzerat.autor = request.user
            novy_inzerat.save()

            # Hromadné nahrání fotek do galerie (getlist je klíčový!)
            extra_fotky = request.FILES.getlist('galerie_fotky')
            for f in extra_fotky:
                InzeratFoto.objects.create(inzerat=novy_inzerat, foto=f)

            messages.success(request, "Inzerát byl úspěšně přidán do Bazaru.")
            return redirect('seznam_inzeratu')
    else:
        form = InzeratForm()

    return render(request, 'inzerce/pridat_inzerat.html', {'form': form})


# 4. ÚPRAVA INZERÁTU
@login_required
def upravit_inzerat(request, pk):
    inzerat = get_object_or_404(Inzerat, pk=pk)

    # Bezpečnostní pojistka
    if inzerat.autor != request.user and not request.user.is_superuser:
        messages.error(request, "Na úpravu tohoto inzerátu nemáte oprávnění.")
        return redirect('seznam_inzeratu')

    if request.method == 'POST':
        # Důležité: instance=inzerat říká Djangu, že upravujeme stávající záznam
        form = InzeratForm(request.POST, request.FILES, instance=inzerat)
        if form.is_valid():
            form.save() # Tady se uloží změny i hlavní obrázek

            # Přidání dalších fotek do galerie, pokud byly vybrány
            extra_fotky = request.FILES.getlist('galerie_fotky')
            for f in extra_fotky:
                InzeratFoto.objects.create(inzerat=inzerat, foto=f)

            messages.success(request, "Inzerát byl úspěšně aktualizován.")
            return redirect('detail_inzeratu', pk=inzerat.pk)
    else:
        form = InzeratForm(instance=inzerat)

    return render(request, 'inzerce/upravit_inzerat.html', {
        'form': form,
        'inzerat': inzerat
    })


# 5. SMAZÁNÍ INZERÁTU
@login_required
def smazat_inzerat(request, pk):
    inzerat = get_object_or_404(Inzerat, pk=pk)

    if inzerat.autor == request.user or request.user.is_superuser:
        inzerat.delete()
        messages.success(request, "Inzerát byl úspěšně odstraněn.")
    else:
        messages.error(request, "Nemáte oprávnění ke smazání tohoto inzerátu.")

    return redirect('seznam_inzeratu')