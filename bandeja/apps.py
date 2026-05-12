from django.apps import AppConfig


class BandejaConfig(AppConfig):
    name = "bandeja"
    label = "bandeja"
    verbose_name = "Bandeja omnichannel"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Cargar acciones built-in del registry de macros
        from bandeja.macros import builtin  # noqa: F401
