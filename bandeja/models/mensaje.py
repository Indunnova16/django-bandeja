from django.conf import settings
from django.db import models

from bandeja.models import TimeStampedModel


class Mensaje(TimeStampedModel):
    """Un mensaje individual en una conversación.

    El FK a `Conversacion` se agrega en Fase 3 del roadmap. Por ahora los
    mensajes se agrupan implícitamente por `contacto`.
    """

    DIRECCION_CHOICES = [
        ("entrante", "Entrante"),
        ("saliente", "Saliente"),
    ]
    TIPO_CONTENIDO_CHOICES = [
        ("texto", "Texto"),
        ("audio", "Audio"),
        ("imagen", "Imagen"),
        ("documento", "Documento"),
        ("sticker", "Sticker"),
        ("ubicacion", "Ubicación"),
        ("otro", "Otro"),
    ]

    contacto = models.ForeignKey(
        "bandeja.Contacto", on_delete=models.CASCADE, related_name="mensajes"
    )
    canal = models.ForeignKey(
        "bandeja.Canal", on_delete=models.PROTECT, related_name="mensajes"
    )
    conversacion = models.ForeignKey(
        "bandeja.Conversacion",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="mensajes",
        help_text="Conversación a la que pertenece. Nullable durante migraciones.",
    )
    direccion = models.CharField(max_length=10, choices=DIRECCION_CHOICES)
    tipo_contenido = models.CharField(
        max_length=15, choices=TIPO_CONTENIDO_CHOICES, default="texto"
    )
    contenido = models.TextField(blank=True)
    wa_message_id = models.CharField(max_length=128, unique=True)
    es_nota_privada = models.BooleanField(
        default=False,
        help_text="Si True, el mensaje no se envía al cliente — solo visible para agentes.",
    )
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mensajes_enviados",
        help_text="Usuario que envió el mensaje (solo direccion=saliente).",
    )
    timestamp = models.DateTimeField()

    class Meta:
        app_label = "bandeja"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["contacto", "-timestamp"]),
            models.Index(fields=["direccion", "-timestamp"]),
            models.Index(fields=["conversacion", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.contacto.nombre} [{self.direccion}] {self.timestamp:%Y-%m-%d %H:%M}"
