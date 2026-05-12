from django.conf import settings
from django.db import models


class Mencion(models.Model):
    """Mención `@usuario` en una nota privada.

    Se genera al persistir un Mensaje con `es_nota_privada=True` cuyo
    contenido contiene `@username`.
    """

    mensaje = models.ForeignKey(
        "bandeja.Mensaje", on_delete=models.CASCADE, related_name="menciones"
    )
    mencionado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="menciones_recibidas",
    )
    creado_at = models.DateTimeField(auto_now_add=True)
    leida_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "bandeja"
        ordering = ["-creado_at"]
        unique_together = [("mensaje", "mencionado")]

    def __str__(self):
        return f"@{self.mencionado} en msg#{self.mensaje_id}"
