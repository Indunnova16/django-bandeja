"""Django settings para correr los tests del paquete bandeja en aislamiento."""

SECRET_KEY = "test-only-not-secret"
DEBUG = True
USE_TZ = True
TIME_ZONE = "America/Bogota"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "bandeja",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
            ],
        },
    },
]

ROOT_URLCONF = "tests.urls"

LOGIN_URL = "/login/"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Defaults bandeja (lo que un huésped configuraría)
BANDEJA_CHANNELS = {
    "principal": {
        "adapter": "bandeja.channels.whatsapp_cloud.WhatsAppCloudAdapter",
        "phone_number_id": "test-phone-id",
        "verify_token": "test-verify",
        "app_secret": "test-secret",
        "access_token": "test-token",
        "display_name": "Test Channel",
    },
}
BANDEJA_SLA_PRIMERA_RESPUESTA_MIN = 15
