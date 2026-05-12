from django.db import models

from bandeja.models import TimeStampedModel


class Contacto(TimeStampedModel):
    """Contacto al otro lado del canal (cliente / lead).

    `wa_phone` se mantiene como identificador canónico cuando el canal es
    WhatsApp. Para canales tipo email/IG la identificación primaria puede
    quedar en `notas` o agregar campos en futuras versiones.
    """

    TIPO_CHOICES = [
        ("lead", "Lead"),
        ("cliente", "Cliente"),
        ("mayorista", "Mayorista / empresa"),
        ("descartado", "Descartado"),
        ("desconocido", "No clasificado"),
    ]
    FUENTE_CHOICES = [
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("tiktok", "TikTok"),
        ("referido", "Referido"),
        ("web", "Sitio web"),
        ("directo", "Directo / desconocido"),
        ("otro", "Otro"),
    ]

    wa_phone = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=200)
    empresa = models.CharField(max_length=200, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="lead")
    fuente = models.CharField(max_length=20, choices=FUENTE_CHOICES, default="directo")
    notas = models.TextField(blank=True)
    fecha_primer_mensaje = models.DateTimeField(null=True, blank=True)
    fecha_ultimo_mensaje = models.DateTimeField(null=True, blank=True)
    fusionado_en = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="fusionados",
        help_text="Contacto destino si éste fue fusionado.",
    )

    class Meta:
        app_label = "bandeja"
        ordering = ["-fecha_ultimo_mensaje"]

    def __str__(self):
        return f"{self.nombre} ({self.wa_phone})"
