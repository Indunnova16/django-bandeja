from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from bandeja.models import TimeStampedModel


class Conversacion(TimeStampedModel):
    """Una conversación es un hilo de mensajes con un contacto, con ciclo de
    vida propio independiente del estado comercial del huésped.

    Estados:
    - abierta: ciclo activo, requiere atención
    - pendiente: esperando respuesta del cliente
    - pospuesta: snooze hasta `pospuesta_hasta`
    - resuelta: cerrada por el agente

    El huésped enlaza su modelo de dominio (Oportunidad, Cotización, Pedido)
    vía `objeto_negocio` (GenericForeignKey). El paquete no asume nada.
    """

    ESTADO_CHOICES = [
        ("abierta", "Abierta"),
        ("pendiente", "Pendiente"),
        ("pospuesta", "Pospuesta"),
        ("resuelta", "Resuelta"),
    ]
    ESTADOS_ACTIVOS = ("abierta", "pendiente")

    contacto = models.ForeignKey(
        "bandeja.Contacto",
        on_delete=models.CASCADE,
        related_name="conversaciones",
    )
    canal = models.ForeignKey(
        "bandeja.Canal", on_delete=models.PROTECT, related_name="conversaciones"
    )
    asesor_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="conversaciones_asignadas",
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="abierta")
    pospuesta_hasta = models.DateTimeField(null=True, blank=True)
    primera_respuesta_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp del primer mensaje saliente del agente. Para SLA.",
    )
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_ultimo_mensaje = models.DateTimeField(null=True, blank=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    # Enlace al objeto de negocio del huésped (Oportunidad, Cotización, …)
    objeto_ct = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL
    )
    objeto_id = models.PositiveIntegerField(null=True, blank=True)
    objeto_negocio = GenericForeignKey("objeto_ct", "objeto_id")

    class Meta:
        app_label = "bandeja"
        ordering = ["-fecha_ultimo_mensaje", "-fecha_apertura"]
        indexes = [
            models.Index(fields=["estado", "-fecha_ultimo_mensaje"]),
            models.Index(fields=["asesor_asignado", "estado"]),
            models.Index(fields=["objeto_ct", "objeto_id"]),
        ]

    def __str__(self):
        return f"#{self.pk} {self.contacto.nombre} [{self.get_estado_display()}]"

    @property
    def esta_activa(self) -> bool:
        return self.estado in self.ESTADOS_ACTIVOS
