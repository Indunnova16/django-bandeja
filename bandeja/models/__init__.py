"""Modelos del paquete bandeja.

Los modelos concretos se agregarán en fases posteriores:
- Fase 1: Contacto, Mensaje, Canal, BandejaAgentProfile
- Fase 3: Conversacion, Etiqueta, RespuestaGuardada
- Fase 4: Macro, EjecucionMacro
- Fase 5: EncuestaCSAT, Mencion, BitacoraContacto
"""

from django.db import models


class TimeStampedModel(models.Model):
    """Modelo base abstracto con created_at / updated_at."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        app_label = "bandeja"
