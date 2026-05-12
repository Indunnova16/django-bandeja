"""Estrategia de asignación: el agente activo con menos oportunidades abiertas.

Sirve como default mientras no haya turnos (`RoundRobinByShift` llega en
Fase 4). El criterio "menos abiertas" se basa en
`Oportunidad.asesor_asignado` cuando la app huésped expone esa relación.
Si el huésped no tiene Oportunidad, se cae al primer agente activo por id.
"""
from __future__ import annotations

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from bandeja.assignment.base import AgentAssignmentStrategy

_ESTADOS_ABIERTOS = (
    "saludo_inicial",
    "cotizando",
    "propuesta_enviada",
    "en_negociacion",
    "sin_respuesta",
    "abandonado_por_cliente",
)


class LeastBusyStrategy(AgentAssignmentStrategy):
    def assign(self, conversacion=None):
        User = get_user_model()
        qs = User.objects.filter(is_active=True, bandeja_profile__activo=True)

        # Preferir el conteo de conversaciones bandeja activas (genérico).
        qs = qs.annotate(
            abiertas=Count(
                "conversaciones_asignadas",
                filter=Q(conversaciones_asignadas__estado__in=("abierta", "pendiente")),
            )
        ).order_by("abiertas", "id")
        return qs.first()
