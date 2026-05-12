"""Acciones de macro genéricas que vienen con el paquete bandeja.

Las apps huéspedes pueden registrar acciones adicionales específicas de su
dominio (ej. `set_oportunidad_estado` en LaCintería).
"""
from __future__ import annotations

from django.utils import timezone

from bandeja.macros.registry import MacroError, register_action
from bandeja.models import (
    ConversacionEtiqueta,
    Etiqueta,
    RespuestaGuardada,
)


@register_action("agregar_etiqueta")
def agregar_etiqueta(ejecucion, *, slug: str, **_):
    try:
        etiqueta = Etiqueta.objects.get(slug=slug, activa=True)
    except Etiqueta.DoesNotExist as exc:
        raise MacroError(f"Etiqueta '{slug}' no existe o está inactiva") from exc
    ConversacionEtiqueta.objects.get_or_create(
        conversacion=ejecucion.conversacion,
        etiqueta=etiqueta,
        defaults={"created_by": ejecucion.autor},
    )


@register_action("enviar_respuesta_guardada")
def enviar_respuesta_guardada(ejecucion, *, slug: str, **_):
    from bandeja.services.outbound import send_outbound

    try:
        rg = RespuestaGuardada.objects.get(slug=slug, activa=True)
    except RespuestaGuardada.DoesNotExist as exc:
        raise MacroError(f"Respuesta guardada '{slug}' no existe") from exc

    canal_slug = ejecucion.conversacion.canal.slug
    send_outbound(
        canal_slug,
        ejecucion.conversacion.contacto,
        rg.cuerpo,
        usuario=ejecucion.autor,
        conversacion=ejecucion.conversacion,
    )
    rg.usada_n_veces = (rg.usada_n_veces or 0) + 1
    rg.save(update_fields=["usada_n_veces", "updated_at"])


@register_action("cerrar_conversacion")
def cerrar_conversacion(ejecucion, **_):
    from bandeja.signals import conversacion_resuelta

    conv = ejecucion.conversacion
    if conv.estado == "resuelta":
        return
    conv.estado = "resuelta"
    conv.fecha_resolucion = timezone.now()
    conv.save(update_fields=["estado", "fecha_resolucion", "updated_at"])
    conversacion_resuelta.send(
        sender=type(conv), conversacion=conv, resuelta_por=ejecucion.autor,
    )


@register_action("posponer_conversacion")
def posponer_conversacion(ejecucion, *, hasta: str, **_):
    """`hasta` es ISO 8601 datetime, ej. '2026-05-13T09:00:00-05:00'."""
    from datetime import datetime

    try:
        ts = datetime.fromisoformat(hasta)
    except ValueError as exc:
        raise MacroError(f"`hasta` inválido: {hasta!r}") from exc
    conv = ejecucion.conversacion
    conv.estado = "pospuesta"
    conv.pospuesta_hasta = ts
    conv.save(update_fields=["estado", "pospuesta_hasta", "updated_at"])


@register_action("asignar_asesor")
def asignar_asesor_action(ejecucion, *, username: str, **_):
    from django.contrib.auth import get_user_model
    from bandeja.signals import agente_asignado

    User = get_user_model()
    try:
        user = User.objects.get(username=username, is_active=True)
    except User.DoesNotExist as exc:
        raise MacroError(f"Usuario '{username}' no existe o inactivo") from exc

    conv = ejecucion.conversacion
    anterior = conv.asesor_asignado
    conv.asesor_asignado = user
    conv.save(update_fields=["asesor_asignado", "updated_at"])
    agente_asignado.send(
        sender=type(conv),
        conversacion=conv,
        agente_anterior=anterior,
        agente_nuevo=user,
    )
