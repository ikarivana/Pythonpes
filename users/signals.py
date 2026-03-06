from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import ProfilMajitele

@receiver(post_save, sender=User)
def vytvor_profil_uzivatele(sender, instance, created, **kwargs):
    if created:
        ProfilMajitele.objects.create(uzivatel=instance)