"""Ejecutor de macros: itera pasos, llama acciones, registra EjecucionMacro."""
from __future__ import annotations

import logging

from bandeja.macros.registry import MacroError, get_action
from bandeja.models import EjecucionMacro

logger = logging.getLogger("bandeja.macros.executor")


def ejecutar_macro(macro, conversacion, autor=None) -> EjecucionMacro:
    """Ejecuta los pasos de la macro sobre la conversación.

    Devuelve `EjecucionMacro` con `exitoso=True/False` y el detalle de
    pasos ejecutados. Si un paso falla con `MacroError`, los pasos
    siguientes NO se ejecutan.
    """
    ejecucion = EjecucionMacro(
        macro=macro,
        conversacion=conversacion,
        autor=autor if (autor and getattr(autor, "is_authenticated", True)) else None,
    )
    ejecucion.save()

    pasos_ok: list[dict] = []
    try:
        for paso in macro.pasos or []:
            action_slug = paso.get("action")
            args = paso.get("args", {}) or {}
            if not action_slug:
                raise MacroError(f"Paso sin 'action': {paso!r}")
            fn = get_action(action_slug)
            fn(ejecucion, **args)
            pasos_ok.append({"action": action_slug, "args": args})
        ejecucion.exitoso = True
    except MacroError as exc:
        ejecucion.exitoso = False
        ejecucion.error = str(exc)
        logger.warning("Macro '%s' falló: %s", macro.slug, exc)
    except Exception as exc:  # noqa: BLE001
        ejecucion.exitoso = False
        ejecucion.error = f"Error inesperado: {exc}"
        logger.exception("Macro '%s' falló con excepción no controlada", macro.slug)

    ejecucion.pasos_ejecutados = pasos_ok
    ejecucion.save(update_fields=["exitoso", "error", "pasos_ejecutados"])
    return ejecucion
