"""Procesa mensajes entrantes (todos los canales) y dispara señales.

Este es el punto único de entrada después del webhook view. Cada
`InboundMessage` se transforma en `Contacto` + `Mensaje` persistidos, se
asigna a un agente vía la estrategia configurada, y se notifica al
dominio huésped vía señales.
"""
from __future__ import annotations

import logging

from django.utils.module_loading import import_string

from bandeja import conf
from bandeja.channels.base import ChannelAdapter, InboundMessage
from bandeja.models import Canal, Contacto, Conversacion, Mensaje
from bandeja.signals import (
    agente_asignado,
    conversacion_creada,
    mensaje_recibido,
)

logger = logging.getLogger("bandeja.services.intake")


def _resolver_canal(adapter: ChannelAdapter, inbound: InboundMessage) -> Canal:
    phone_id = inbound.canal_metadata.get("phone_number_id", "")
    if hasattr(adapter, "resolver_canal"):
        return adapter.resolver_canal(phone_id)
    # Default: canal por slug
    canal, _ = Canal.objects.get_or_create(
        slug=adapter.slug,
        defaults={
            "tipo": "whatsapp",
            "phone_number_id": phone_id,
            "display_name": adapter.config.get("display_name", adapter.slug),
        },
    )
    return canal


def _asignar_agente(conversacion: Conversacion):
    """Aplica la estrategia configurada. Devuelve User o None."""
    try:
        strategy_cls = import_string(conf.get_assignment_strategy_path())
    except ImportError:
        logger.warning("BANDEJA_ASSIGNMENT_STRATEGY no importable")
        return None
    return strategy_cls().assign(conversacion)


def _obtener_o_crear_conversacion(contacto: Contacto, canal: Canal) -> tuple[Conversacion, bool]:
    """Busca conversación activa del contacto; si no hay, crea una nueva.

    Devuelve (conversacion, created).
    """
    activa = (
        Conversacion.objects.filter(
            contacto=contacto,
            estado__in=Conversacion.ESTADOS_ACTIVOS,
        )
        .order_by("-fecha_apertura")
        .first()
    )
    if activa:
        return activa, False
    conversacion = Conversacion.objects.create(
        contacto=contacto, canal=canal, estado="abierta",
    )
    return conversacion, True


def process_inbound(adapter: ChannelAdapter, inbounds: list[InboundMessage]) -> int:
    """Persiste mensajes entrantes y dispara señales. Devuelve cantidad creada."""
    creados = 0
    for inbound in inbounds:
        canal = _resolver_canal(adapter, inbound)
        contacto, contacto_created = Contacto.objects.get_or_create(
            wa_phone=inbound.sender_id,
            defaults={
                "nombre": inbound.sender_name or inbound.sender_id,
                "fecha_primer_mensaje": inbound.timestamp,
            },
        )
        contacto.fecha_ultimo_mensaje = inbound.timestamp
        if contacto_created and not contacto.fecha_primer_mensaje:
            contacto.fecha_primer_mensaje = inbound.timestamp
        contacto.save(
            update_fields=["fecha_ultimo_mensaje", "fecha_primer_mensaje", "updated_at"]
        )

        conversacion, conv_created = _obtener_o_crear_conversacion(contacto, canal)

        mensaje, mensaje_created = Mensaje.objects.get_or_create(
            wa_message_id=inbound.external_id,
            defaults={
                "contacto": contacto,
                "canal": canal,
                "conversacion": conversacion,
                "direccion": "entrante",
                "tipo_contenido": inbound.tipo_contenido,
                "contenido": inbound.contenido,
                "timestamp": inbound.timestamp,
            },
        )
        if not mensaje_created:
            continue
        creados += 1

        # Actualizar último mensaje de la conversación
        if not conversacion.fecha_ultimo_mensaje or inbound.timestamp > conversacion.fecha_ultimo_mensaje:
            conversacion.fecha_ultimo_mensaje = inbound.timestamp
            update_fields = ["fecha_ultimo_mensaje", "updated_at"]
            if conv_created:
                # Asignar agente automáticamente al crear conversación
                agente = _asignar_agente(conversacion)
                if agente:
                    conversacion.asesor_asignado = agente
                    update_fields.append("asesor_asignado")
            conversacion.save(update_fields=update_fields)

        if conv_created:
            conversacion_creada.send(
                sender=Conversacion,
                conversacion=conversacion,
                contacto=contacto,
                canal=canal,
                contacto_nuevo=contacto_created,
            )
            if conversacion.asesor_asignado_id:
                agente_asignado.send(
                    sender=Conversacion,
                    conversacion=conversacion,
                    agente_anterior=None,
                    agente_nuevo=conversacion.asesor_asignado,
                )

        mensaje_recibido.send(
            sender=Mensaje,
            mensaje=mensaje,
            contacto=contacto,
            canal=canal,
            conversacion=conversacion,
            contacto_nuevo=contacto_created,
        )

    return creados
