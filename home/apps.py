from django.apps import AppConfig

class HomeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'home'
    verbose_name = 'Mapa a služby'

    def ready(self):
        # I v aplikaci Home se budou signály hodit,
        # např. pro automatické promazávání fotek služeb po smazání z mapy.
        try:
            import home.signals
        except ImportError:
            pass

