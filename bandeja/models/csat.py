from django.db import models

from bandeja.models import TimeStampedModel


class EncuestaCSAT(TimeStampedModel):
    """Encuesta CSAT enviada al cierre de una conversación / venta ganada.

    Estados:
    - `enviada_at` set: ya se envió HSM al cliente
    - `puntaje` set: el cliente respondió
    Si `puntaje is None` después de N días, se considera no respondida.
    """

    conversacion = models.ForeignKey(
        "bandeja.Conversacion", on_delete=models.CASCADE, related_name="csats"
    )
    contacto = models.ForeignKey(
        "bandeja.Contacto", on_delete=models.CASCADE, related_name="csats"
    )
    enviada_at = models.DateTimeField(null=True, blank=True)
    puntaje = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="1-5. None = pendiente de respuesta.",
    )
    comentario = models.TextField(blank=True)
    respondida_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "bandeja"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["conversacion", "-created_at"]),
            models.Index(fields=["puntaje", "-respondida_at"]),
        ]

    def __str__(self):
        return f"CSAT conv#{self.conversacion_id} = {self.puntaje or '?'}"
