from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Uživatelé a psi'

    def ready(self):
        # Místo 'import users.signals' napiš:
        from . import signals

