"""Acceso centralizado a settings del paquete con defaults."""
from django.conf import settings


def get_channels() -> dict:
    return getattr(settings, "BANDEJA_CHANNELS", {})


def get_assignment_strategy_path() -> str:
    return getattr(
        settings,
        "BANDEJA_ASSIGNMENT_STRATEGY",
        "bandeja.assignment.least_busy.LeastBusyStrategy",
    )


def get_shift_resolver_path() -> str | None:
    return getattr(settings, "BANDEJA_SHIFT_RESOLVER", None)


def get_sla_primera_respuesta_min() -> int:
    return int(getattr(settings, "BANDEJA_SLA_PRIMERA_RESPUESTA_MIN", 15))


def is_csat_enabled() -> bool:
    return bool(getattr(settings, "BANDEJA_CSAT_ENABLED", False))
