"""Django settings para correr los tests del paquete bandeja en aislamiento."""

SECRET_KEY = "test-only-not-secret"
DEBUG = True
USE_TZ = True
TIME_ZONE = "America/Bogota"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "bandeja",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Defaults bandeja (lo que un huésped configuraría)
BANDEJA_CHANNELS = {}
BANDEJA_SLA_PRIMERA_RESPUESTA_MIN = 15
