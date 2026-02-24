from django.apps import apps
from django.utils import timezone

def counts(request):
    """Vrací počty inzerátů pro přihlášeného uživatele."""
    if request.user.is_authenticated:
        try:
            # Explicitně hledáme v aplikaci 'inzerce'
            Inzerat = apps.get_model('inzerce', 'Inzerat')
            pocet = Inzerat.objects.filter(autor=request.user).count()
            return {'moje_inzeraty_count': pocet}
        except (LookupError, ImportError):
            # Záložní plán pro případ, že model ještě neexistuje nebo je v 'home'
            return {'moje_inzeraty_count': 0}
    return {'moje_inzeraty_count': 0}

def premium_warning(request):
    """Vypočítá dny do konce prémia a aktivuje varování."""
    if request.user.is_authenticated:
        profil = getattr(request.user, 'profil', None)
        if profil and profil.is_premium and profil.premium_do:
            # Výpočet zbývajících dnů
            zbyva = (profil.premium_do - timezone.now().date()).days
            return {
                'premium_zbyva_dni': zbyva,
                'premium_warning_active': zbyva <= 7  # Aktivuje se týden předem
            }
    return {
        'premium_warning_active': False,
        'premium_zbyva_dni': 0
    }