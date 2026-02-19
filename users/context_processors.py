from django.utils import timezone

def premium_warning(request):
    if request.user.is_authenticated:
        # Tady by měla být vaše logika pro varování
        # Např. pokud profilu končí prémium
        profil = getattr(request.user, 'profil', None)
        if profil and profil.is_premium and profil.premium_do:
            # logika pro výpočet zbývajících dnů atd.
            return {'premium_warning_active': True}
    return {'premium_warning_active': False}

from django.apps import apps

def counts(request):
    if request.user.is_authenticated:
        # ZDE POZOR: Pokud se tvoje složka s inzeráty jmenuje 'inzerce',
        # změň první slovo v uvozovkách na 'inzerce'
        try:
            Inzerat = apps.get_model('inzerce', 'Inzerat')
            pocet = Inzerat.objects.filter(autor=request.user).count()
            return {'moje_inzeraty_count': pocet}
        except (LookupError, ImportError):
            # Pokud se aplikace nejmenuje inzerce, zkusíme 'home'
            try:
                Inzerat = apps.get_model('home', 'Inzerat')
                pocet = Inzerat.objects.filter(autor=request.user).count()
                return {'moje_inzeraty_count': pocet}
            except:
                return {'moje_inzeraty_count': 0}
    return {'moje_inzeraty_count': 0}