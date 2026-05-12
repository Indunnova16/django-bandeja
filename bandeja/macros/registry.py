"""Registro global de acciones de macro."""
from __future__ import annotations

from typing import Callable


class MacroError(Exception):
    """Fallo recuperable en una acción de macro. El executor lo captura,
    registra en EjecucionMacro.error y aborta el resto de pasos."""


_REGISTRY: dict[str, Callable] = {}


def register_action(slug: str):
    """Decorador para registrar una acción bajo un `slug`."""

    def decorator(fn: Callable) -> Callable:
        if slug in _REGISTRY:
            raise RuntimeError(f"Action '{slug}' ya está registrada por {_REGISTRY[slug]}")
        _REGISTRY[slug] = fn
        return fn

    return decorator


def get_action(slug: str) -> Callable:
    if slug not in _REGISTRY:
        raise MacroError(f"Acción de macro desconocida: {slug!r}")
    return _REGISTRY[slug]


def list_actions() -> list[str]:
    return sorted(_REGISTRY)
