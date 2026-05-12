from django.conf import settings
from django.db import models


class BitacoraContacto(models.Model):
    """Auditoría append-only de acciones sobre contactos (merge, etc.)."""

    contacto = models.ForeignKey(
        "bandeja.Contacto", on_delete=models.CASCADE, related_name="bitacora"
    )
    accion = models.CharField(max_length=40)  # 'merge_target', 'merge_source', ...
    detalle = models.JSONField(default=dict)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "bandeja"
        ordering = ["-timestamp"]
