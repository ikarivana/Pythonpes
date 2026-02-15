from django.contrib import admin
# Změň GalerieFotka na Galerie a GalerieVideo na Video
from .models import ProfilMajitele, Pes, Uspech, Galerie, Video, Ockovani, ZdravotniZaznam

# Registrace modelů do administrace
admin.site.register(ProfilMajitele)
admin.site.register(Pes)
admin.site.register(Uspech)
admin.site.register(Galerie)  # Opraveno
admin.site.register(Video)    # Opraveno
admin.site.register(Ockovani)
admin.site.register(ZdravotniZaznam)
