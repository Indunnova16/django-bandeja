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

        # Si el huésped tiene un modelo Oportunidad con FK asesor_asignado,
        # anotamos cuántas oportunidades abiertas tiene cada agente.
        if apps.is_installed("apps.comercial"):
            try:
                qs = qs.annotate(
                    abiertas=Count(
                        "oportunidades_asignadas",
                        filter=Q(oportunidades_asignadas__estado__in=_ESTADOS_ABIERTOS),
                    )
                ).order_by("abiertas", "id")
            except Exception:  # noqa: BLE001
                qs = qs.order_by("id")
        else:
            qs = qs.order_by("id")

        return qs.first()
