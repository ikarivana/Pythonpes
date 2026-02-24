from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .models import Pes, Ockovani, Notifikace

def hlidac_zdravi_premium():
    dnes = timezone.now().date()
    pripominka_za = dnes + timedelta(days=3)

    # --- 1. OČKOVÁNÍ ---
    ockovani_k_pripomnuti = Ockovani.objects.filter(
        datum_pristi_navstevy=pripominka_za,
        pes__majitel__is_premium=True
    )
    for ocko in ockovani_k_pripomnuti:
        send_mail(
            f"💉 Připomínka očkování: {ocko.pes.jmeno}",
            f"Ahoj! Za 3 dny má {ocko.pes.jmeno} termín očkování ({ocko.nazev_vakciny}).",
            'podpora@epes.online',
            [ocko.pes.majitel.uzivatel.email]
        )
        # Přidáme notifikaci na web
        Notifikace.objects.create(
            prijemce=ocko.pes.majitel.uzivatel,
            zprava=f"💉 Blíží se očkování ({ocko.nazev_vakciny}) u psa {ocko.pes.jmeno}!",
            typ='zdravotni'
        )

    # --- 2. KLÍŠŤATA A ODČERVENÍ ---
    vsichni_psi = Pes.objects.filter(majitel__is_premium=True)
    for pes in vsichni_psi:
        # Klíšťata
        if pes.pristi_klistata == pripominka_za:
            send_mail(
                f"🐜 Ochrana proti parazitům: {pes.jmeno}",
                f"Ahoj! Za 3 dny vyprší ochrana u {pes.jmeno}.",
                'podpora@epes.online',
                [pes.majitel.uzivatel.email]
            )
            Notifikace.objects.create(
                prijemce=pes.majitel.uzivatel,
                zprava=f"🐜 Za 3 dny vyprší ochrana proti klíšťatům u psa {pes.jmeno}!",
                typ='zdravotni'
            )

        # Odčervení
        if pes.pristi_odcerveni == pripominka_za:
            send_mail(
                f"💊 Čas na odčervení: {pes.jmeno}",
                f"Ahoj, nezapomeň, že za 3 dny by měl být {pes.jmeno} znovu odčerven.",
                'podpora@epes.online',
                [pes.majitel.uzivatel.email]
            )
            Notifikace.objects.create(
                prijemce=pes.majitel.uzivatel,
                zprava=f"💊 Nezapomeňte na odčervení psa {pes.jmeno} za 3 dny.",
                typ='zdravotni'
            )