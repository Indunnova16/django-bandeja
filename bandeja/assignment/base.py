"""Contrato de las estrategias de asignación."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


class AgentAssignmentStrategy(ABC):
    """Decide qué agente (User) atiende una conversación nueva.

    El paquete instancia la estrategia una sola vez por proceso (lazy),
    así que el estado entre llamadas (p. ej. cursor de round-robin) puede
    persistirse en BD vía `BandejaAgentProfile.ultima_asignacion_at`, no en
    memoria.
    """

    @abstractmethod
    def assign(self, conversacion=None) -> "AbstractBaseUser | None":
        """Devuelve el `User` asignado o `None` si nadie está disponible.

        `conversacion` es opcional para mantener compatibilidad con uso
        actual (legacy `asignar_asesor()` sin argumentos). En Fase 3, una
        vez `Conversacion` exista, la estrategia podrá usar `contacto`,
        `canal`, etiquetas, etc. para decidir.
        """
