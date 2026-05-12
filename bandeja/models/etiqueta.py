from django.conf import settings
from django.db import models

from bandeja.models import TimeStampedModel


class Etiqueta(TimeStampedModel):
    """Etiqueta libre aplicable a Contactos y Conversaciones."""

    slug = models.SlugField(max_length=64, unique=True)
    nombre = models.CharField(max_length=80)
    color = models.CharField(
        max_length=7, default="#94a3b8",
        help_text="Color hex para el chip, ej. #2563eb",
    )
    activa = models.BooleanField(default=True)

    class Meta:
        app_label = "bandeja"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class ContactoEtiqueta(models.Model):
    contacto = models.ForeignKey(
        "bandeja.Contacto", on_delete=models.CASCADE, related_name="etiquetas_rel"
    )
    etiqueta = models.ForeignKey(Etiqueta, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )

    class Meta:
        app_label = "bandeja"
        unique_together = [("contacto", "etiqueta")]


class ConversacionEtiqueta(models.Model):
    conversacion = models.ForeignKey(
        "bandeja.Conversacion", on_delete=models.CASCADE, related_name="etiquetas_rel"
    )
    etiqueta = models.ForeignKey(Etiqueta, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )

    class Meta:
        app_label = "bandeja"
        unique_together = [("conversacion", "etiqueta")]
