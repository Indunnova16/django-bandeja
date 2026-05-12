"""Reportes por asesora — métricas agregadas."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from bandeja.models import Conversacion, Mensaje


def reporte_asesoras(desde: datetime, hasta: datetime) -> list[dict]:
    """Métricas por asesora dentro del rango:

    - conversaciones_abiertas_en_rango
    - conversaciones_resueltas
    - tiempo_medio_primera_respuesta_seg
    - mensajes_salientes
    """
    User = get_user_model()
    activas = User.objects.filter(bandeja_profile__isnull=False).distinct()

    # Conversaciones asignadas
    conv_qs = Conversacion.objects.filter(
        fecha_apertura__gte=desde, fecha_apertura__lte=hasta,
    )
    conv_por_asesor = (
        conv_qs.filter(asesor_asignado__isnull=False)
        .values("asesor_asignado_id")
        .annotate(
            abiertas_en_rango=Count("id"),
            resueltas=Count("id", filter=Q(estado="resuelta")),
        )
    )
    conv_map = {r["asesor_asignado_id"]: r for r in conv_por_asesor}

    # Tiempo medio primera respuesta — calcular en Python (portable)
    deltas_por_asesor = defaultdict(list)
    for c in conv_qs.filter(
        asesor_asignado__isnull=False, primera_respuesta_at__isnull=False,
    ).only("asesor_asignado_id", "fecha_apertura", "primera_respuesta_at"):
        deltas_por_asesor[c.asesor_asignado_id].append(
            (c.primera_respuesta_at - c.fecha_apertura).total_seconds()
        )

    # Mensajes salientes por enviado_por
    mensajes_qs = Mensaje.objects.filter(
        direccion="saliente",
        timestamp__gte=desde,
        timestamp__lte=hasta,
        enviado_por__isnull=False,
    )
    msgs_por_asesor = dict(
        mensajes_qs.values_list("enviado_por_id").annotate(n=Count("id")).values_list("enviado_por_id", "n")
    )

    out = []
    for user in activas:
        deltas = deltas_por_asesor.get(user.id, [])
        avg = sum(deltas) / len(deltas) if deltas else None
        c = conv_map.get(user.id, {})
        out.append({
            "user_id": user.id,
            "username": user.username,
            "nombre": (
                getattr(user.bandeja_profile, "nombre_display", "")
                or user.get_full_name()
                or user.username
            ),
            "conversaciones_abiertas_en_rango": c.get("abiertas_en_rango", 0),
            "conversaciones_resueltas": c.get("resueltas", 0),
            "tiempo_medio_primera_respuesta_seg": avg,
            "mensajes_salientes": msgs_por_asesor.get(user.id, 0),
        })
    out.sort(key=lambda r: r["conversaciones_abiertas_en_rango"], reverse=True)
    return out
