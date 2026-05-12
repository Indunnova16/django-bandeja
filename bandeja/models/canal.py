from django.db import models

from bandeja.models import TimeStampedModel


class Canal(TimeStampedModel):
    """Canal de mensajería conectado (WhatsApp, IG, FB, TikTok, email, …).

    El `slug` identifica al canal en `settings.BANDEJA_CHANNELS` y en URLs
    de webhook (`/bandeja/webhook/<slug>/`).
    """

    TIPO_CHOICES = [
        ("whatsapp", "WhatsApp"),
        ("instagram", "Instagram"),
        ("facebook", "Facebook Messenger"),
        ("tiktok", "TikTok"),
        ("email", "Email"),
        ("webhook", "Webhook genérico"),
    ]

    slug = models.SlugField(max_length=64, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="whatsapp")
    display_name = models.CharField(max_length=120)
    phone_number_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="WhatsApp Cloud API phone_number_id. Solo para tipo=whatsapp.",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        app_label = "bandeja"
        ordering = ["tipo", "display_name"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.display_name}"
