"""Modelos del paquete bandeja.

Fases:
- Fase 1: Contacto, Mensaje, Canal, BandejaAgentProfile (este archivo)
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


from bandeja.models.canal import Canal  # noqa: E402, F401
from bandeja.models.contacto import Contacto  # noqa: E402, F401
from bandeja.models.mensaje import Mensaje  # noqa: E402, F401
from bandeja.models.agente import BandejaAgentProfile  # noqa: E402, F401

__all__ = [
    "TimeStampedModel",
    "Canal",
    "Contacto",
    "Mensaje",
    "BandejaAgentProfile",
]
