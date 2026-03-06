from django.apps import AppConfig

class InzerceConfig(AppConfig): # Tady musí být InzerceConfig, ne UsersConfig!
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inzerce'
    verbose_name = 'Bazar a Inzerce'

    def ready(self):
        try:
            from . import signals
        except ImportError:
            pass