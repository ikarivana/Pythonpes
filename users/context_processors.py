from .models import Notifikace

def counts(request):
    if request.user.is_authenticated:
        # Použijeme tvůj nový related_name 'prijate_notifikace'
        return {
            'pocet_notifikaci': request.user.prijate_notifikace.filter(precteno=False).count()
        }
    return {'pocet_notifikaci': 0}