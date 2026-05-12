"""Estrategia round-robin entre agentes en turno.

Consulta `settings.BANDEJA_SHIFT_RESOLVER` (callable importable que devuelve
`QuerySet[User]` con los agentes en turno ahora). Si nadie está en turno,
cae al fallback `LeastBusyStrategy`.

Cola justa: el agente con `bandeja_profile.ultima_asignacion_at` más antiguo
recibe la siguiente conversación.
"""
from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from django.utils.module_loading import import_string
from django.utils import timezone

from bandeja import conf
from bandeja.assignment.base import AgentAssignmentStrategy
from bandeja.assignment.least_busy import LeastBusyStrategy


_EPOCH = datetime(1970, 1, 1, tzinfo=dt_timezone.utc)


class RoundRobinByShift(AgentAssignmentStrategy):
    def assign(self, conversacion=None):
        resolver_path = conf.get_shift_resolver_path()
        candidates = []
        if resolver_path:
            try:
                resolver = import_string(resolver_path)
                candidates = list(resolver())
            except (ImportError, AttributeError):
                candidates = []

        if not candidates:
            return LeastBusyStrategy().assign(conversacion)

        # Filtrar a los que tienen bandeja_profile activo
        candidates = [
            u for u in candidates
            if getattr(u, "bandeja_profile", None) and u.bandeja_profile.activo
        ]
        if not candidates:
            return LeastBusyStrategy().assign(conversacion)

        # El más antiguamente asignado va primero (cola justa)
        candidates.sort(
            key=lambda u: u.bandeja_profile.ultima_asignacion_at or _EPOCH
        )
        elegido = candidates[0]
        elegido.bandeja_profile.ultima_asignacion_at = timezone.now()
        elegido.bandeja_profile.save(update_fields=["ultima_asignacion_at", "updated_at"])
        return elegido
