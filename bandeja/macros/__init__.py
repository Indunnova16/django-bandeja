"""Sistema de macros: secuencias de acciones ejecutables sobre conversaciones.

API pública:
- `register_action(slug)` — decorador para registrar nuevas acciones
- `get_action(slug)` — lookup
- `ejecutar_macro(macro, conversacion, autor)` — runner

Cada acción es una función con firma:
    def accion(ejecucion: EjecucionMacro, **args) -> None
donde `args` son los kwargs del paso JSON. Lanzar `MacroError` para
señalar fallos recuperables; otras excepciones se capturan en el log.
"""
from bandeja.macros.registry import (  # noqa: F401
    MacroError,
    get_action,
    list_actions,
    register_action,
)
from bandeja.macros.executor import ejecutar_macro  # noqa: F401

__all__ = [
    "MacroError",
    "register_action",
    "get_action",
    "list_actions",
    "ejecutar_macro",
]
