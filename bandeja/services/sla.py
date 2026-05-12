"""Cálculo de SLA de primera respuesta y métricas asociadas."""
from __future__ import annotations

from datetime import timedelta

from django.db.models import Avg, Count, F, Q
from django.utils import timezone

from bandeja import conf
from bandeja.models import Conversacion


def sla_status(conversacion: Conversacion) -> dict:
    """Devuelve estado SLA de una conversación.

    Schema:
        {"respondida": bool, "ok": bool, "tiempo_respuesta": timedelta | None,
         "elapsed": timedelta, "sla_min": int}
    """
    sla_min = conf.get_sla_primera_respuesta_min()
    if conversacion.primera_respuesta_at:
        tiempo = conversacion.primera_respuesta_at - conversacion.fecha_apertura
        return {
            "respondida": True,
            "ok": tiempo <= timedelta(minutes=sla_min),
            "tiempo_respuesta": tiempo,
            "elapsed": tiempo,
            "sla_min": sla_min,
        }
    ahora = timezone.now()
    elapsed = ahora - conversacion.fecha_apertura
    return {
        "respondida": False,
        "ok": elapsed <= timedelta(minutes=sla_min),
        "tiempo_respuesta": None,
        "elapsed": elapsed,
        "sla_min": sla_min,
    }


def conversaciones_en_riesgo():
    """QuerySet de conversaciones entrantes sin respuesta que ya excedieron el SLA."""
    sla_min = conf.get_sla_primera_respuesta_min()
    limite = timezone.now() - timedelta(minutes=sla_min)
    return Conversacion.objects.filter(
        estado__in=("abierta", "pendiente"),
        primera_respuesta_at__isnull=True,
        fecha_apertura__lte=limite,
    )


def metricas_sla(desde, hasta) -> dict:
    qs = Conversacion.objects.filter(fecha_apertura__gte=desde, fecha_apertura__lte=hasta)
    total = qs.count()
    respondidas = qs.filter(primera_respuesta_at__isnull=False)
    n_resp = respondidas.count()

    # Tiempo medio (en segundos) entre apertura y primera respuesta
    avg_seconds = None
    if n_resp:
        respondidas_anotadas = respondidas.annotate(
            delta_seconds=Count("id"),  # placeholder — SQLite no soporta interval avg fácil
        )
        # Cálculo en Python para portabilidad SQLite/Postgres
        deltas = [
            (c.primera_respuesta_at - c.fecha_apertura).total_seconds()
            for c in respondidas
        ]
        avg_seconds = sum(deltas) / len(deltas) if deltas else None

    sla_min = conf.get_sla_primera_respuesta_min()
    en_sla = 0
    if avg_seconds is not None:
        en_sla = sum(
            1 for c in respondidas
            if (c.primera_respuesta_at - c.fecha_apertura).total_seconds() <= sla_min * 60
        )

    return {
        "total": total,
        "respondidas": n_resp,
        "tiempo_medio_segundos": avg_seconds,
        "en_sla": en_sla,
        "pct_en_sla": round(en_sla / n_resp * 100, 1) if n_resp else 0.0,
        "sla_min": sla_min,
    }
