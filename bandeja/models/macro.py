from django.conf import settings
from django.db import models

from bandeja.models import TimeStampedModel


class Macro(TimeStampedModel):
    """Secuencia ordenada de acciones (JSON) ejecutables sobre una conversación.

    Estructura del campo `pasos`:
        [
            {"action": "agregar_etiqueta", "args": {"slug": "perdida-2026"}},
            {"action": "enviar_respuesta_guardada", "args": {"slug": "despedida"}},
            {"action": "cerrar_conversacion"},
        ]

    Cada `action` debe estar registrada con `@register_action` (ver
    `bandeja.macros.registry`). Las acciones genéricas vienen en
    `bandeja.macros.builtin`; las apps huéspedes pueden registrar acciones
    específicas de su dominio.
    """

    slug = models.SlugField(max_length=64, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    pasos = models.JSONField(default=list)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="macros_creadas",
    )
    activa = models.BooleanField(default=True)

    class Meta:
        app_label = "bandeja"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class EjecucionMacro(models.Model):
    """Audit log de cada ejecución de macro."""

    macro = models.ForeignKey(Macro, on_delete=models.CASCADE, related_name="ejecuciones")
    conversacion = models.ForeignKey(
        "bandeja.Conversacion", on_delete=models.CASCADE, related_name="ejecuciones_macro"
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    exitoso = models.BooleanField(default=False)
    pasos_ejecutados = models.JSONField(default=list)
    error = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "bandeja"
        ordering = ["-timestamp"]

    def __str__(self):
        flag = "✓" if self.exitoso else "✗"
        return f"{flag} {self.macro.slug} → conv#{self.conversacion_id}"
