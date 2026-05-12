from django.conf import settings
from django.db import models

from bandeja.models import TimeStampedModel


class RespuestaGuardada(TimeStampedModel):
    """Atajo de respuesta reusable. Se invoca con `/slug` en el composer."""

    slug = models.SlugField(
        max_length=40, unique=True,
        help_text="Atajo. Ej: `medidas`, `precios-mayorista`.",
    )
    titulo = models.CharField(max_length=120)
    cuerpo = models.TextField()
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="respuestas_guardadas",
    )
    activa = models.BooleanField(default=True)
    usada_n_veces = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "bandeja"
        ordering = ["slug"]

    def __str__(self):
        return f"/{self.slug} — {self.titulo}"
