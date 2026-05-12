"""Template tags y filtros del paquete bandeja."""
from django import template

register = template.Library()


@register.filter(name="nombre_asesor")
def nombre_asesor(user) -> str:
    """Display name de un agente.

    Prioridad: bandeja_profile.nombre_display → user.get_full_name() → username.
    """
    if user is None:
        return ""
    profile = getattr(user, "bandeja_profile", None)
    if profile and profile.nombre_display:
        return profile.nombre_display
    full = user.get_full_name() if hasattr(user, "get_full_name") else ""
    return full or getattr(user, "username", "") or ""
