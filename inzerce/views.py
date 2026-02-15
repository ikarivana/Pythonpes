from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Inzerat, InzeratFoto
from .forms import InzeratForm


# HLAVNÍ PŘEHLED INZERÁTŮ
def seznam_inzeratu(request):
    """Zobrazení přehledu inzerátů seřazených podle Premium statusu."""
    # 1. Získání filtrů z URL
    kraj_filtr = request.GET.get('kraj')
    typ_filtr = request.GET.get('typ')
    kategorie_filtr = request.GET.get('kategorie')

    # 2. Základní QuerySet (seřazený primárně podle času)
    inzeraty_queryset = Inzerat.objects.all().order_by('-vytvoreno')

    # 3. Aplikace filtrů
    if kraj_filtr:
        inzeraty_queryset = inzeraty_queryset.filter(kraj=kraj_filtr)
    if typ_filtr:
        inzeraty_queryset = inzeraty_queryset.filter(pohlavi=typ_filtr)
    if kategorie_filtr:
        inzeraty_queryset = inzeraty_queryset.filter(kategorie=kategorie_filtr)

    # 4. SEŘAZENÍ (Python verze): Obejití chyby Unsupported lookup
    # Seřadí seznam tak, aby ti, co mají profil.is_premium = True, byli nahoře.
    inzeraty_list = sorted(
        list(inzeraty_queryset),
        key=lambda x: getattr(x.autor.profil, 'is_premium', False),
        reverse=True
    )

    context = {
        'inzeraty': inzeraty_list,
        'kraje': Inzerat.KRAJE_CHOICES,
    }

    return render(request, 'inzerce/seznam_inzeratu.html', context)


# DETAIL INZERÁTU
def detail_inzeratu(request, pk):
    """Zobrazení detailu jednoho inzerátu s galerií."""
    inzerat = get_object_or_404(Inzerat, pk=pk)
    galerie = inzerat.galerie.all()

    context = {
        'inzerat': inzerat,
        'galerie': galerie,
    }
    return render(request, 'inzerce/detail_inzeratu.html', context)


# PŘIDÁNÍ INZERÁTU (S kontrolou limitu pro neplatiče)
@login_required
def pridat_inzerat(request):
    """Přidání inzerátu: Běžný uživatel max 1, ALFA člen neomezeně."""

    # Kontrola limitu pro ne-premium uživatele
    is_premium = getattr(request.user.profil, 'is_premium', False)
    pocet_starych = Inzerat.objects.filter(autor=request.user).count()

    if not is_premium and pocet_starych >= 1:
        messages.warning(request,
                         "Jako běžný uživatel můžete mít pouze 1 aktivní inzerát. Pro neomezené vkládání aktivujte Členství ALFA.")
        return redirect('cenik')

    if request.method == 'POST':
        form = InzeratForm(request.POST, request.FILES)
        if form.is_valid():
            novy_inzerat = form.save(commit=False)
            novy_inzerat.autor = request.user
            novy_inzerat.save()

            # Hromadné nahrání fotek do galerie
            extra_fotky = request.FILES.getlist('galerie_fotky')
            for f in extra_fotky:
                InzeratFoto.objects.create(inzerat=novy_inzerat, foto=f)

            messages.success(request, "Inzerát byl úspěšně přidán.")
            return redirect('seznam_inzeratu')
    else:
        form = InzeratForm()

    return render(request, 'inzerce/pridat_inzerat.html', {'form': form})


# ÚPRAVA INZERÁTU
@login_required
def upravit_inzerat(request, pk):
    """Úprava existujícího inzerátu autorem nebo adminem."""
    inzerat = get_object_or_404(Inzerat, pk=pk)

    if inzerat.autor != request.user and not request.user.is_superuser:
        messages.error(request, "Na tohle nemáte oprávnění!")
        return redirect('seznam_inzeratu')

    if request.method == 'POST':
        form = InzeratForm(request.POST, request.FILES, instance=inzerat)
        if form.is_valid():
            form.save()

            # Přidání dalších fotek při úpravě
            extra_fotky = request.FILES.getlist('galerie_fotky')
            for f in extra_fotky:
                InzeratFoto.objects.create(inzerat=inzerat, foto=f)

            messages.success(request, "Inzerát byl úspěšně upraven.")
            return redirect('seznam_inzeratu')
    else:
        form = InzeratForm(instance=inzerat)

    return render(request, 'inzerce/upravit_inzerat.html', {'form': form, 'inzerat': inzerat})


# SMAZÁNÍ INZERÁTU
@login_required
def smazat_inzerat(request, pk):
    """Smazání inzerátu."""
    inzerat = get_object_or_404(Inzerat, pk=pk)

    if inzerat.autor == request.user or request.user.is_superuser:
        inzerat.delete()
        messages.success(request, "Inzerát byl smazán.")
    else:
        messages.error(request, "Nemáte oprávnění smazat tento inzerát.")

    return redirect('seznam_inzeratu')