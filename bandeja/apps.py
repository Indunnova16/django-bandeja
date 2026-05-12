from django.apps import AppConfig


class BandejaConfig(AppConfig):
    name = "bandeja"
    label = "bandeja"
    verbose_name = "Bandeja omnichannel"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Aquí se cargarán signals, registries, etc. en fases posteriores
        pass
