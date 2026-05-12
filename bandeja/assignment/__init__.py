"""Estrategias de asignación de agentes a conversaciones.

Una estrategia es una clase que implementa `AgentAssignmentStrategy` y se
configura vía `settings.BANDEJA_ASSIGNMENT_STRATEGY = "<path.to.Strategy>"`.

Estrategias disponibles en el paquete:
- `LeastBusyStrategy` (default) — el agente activo con menos conversaciones
  abiertas asignadas. Sin consideración de turno.
- `RoundRobinByShift` (Fase 4) — round-robin entre agentes en turno,
  consultando un `BANDEJA_SHIFT_RESOLVER` configurado por el huésped.
"""
from bandeja.assignment.base import AgentAssignmentStrategy  # noqa: F401

__all__ = ["AgentAssignmentStrategy"]
