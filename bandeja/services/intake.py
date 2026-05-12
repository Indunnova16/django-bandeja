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
from bandeja.models import Canal, Contacto, Mensaje
from bandeja.signals import mensaje_recibido

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


def _asignar_agente(contacto: Contacto):
    """Aplica la estrategia configurada. Devuelve User o None."""
    try:
        strategy_cls = import_string(conf.get_assignment_strategy_path())
    except ImportError:
        logger.warning("BANDEJA_ASSIGNMENT_STRATEGY no importable")
        return None
    return strategy_cls().assign()


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

        mensaje, mensaje_created = Mensaje.objects.get_or_create(
            wa_message_id=inbound.external_id,
            defaults={
                "contacto": contacto,
                "canal": canal,
                "direccion": "entrante",
                "tipo_contenido": inbound.tipo_contenido,
                "contenido": inbound.contenido,
                "timestamp": inbound.timestamp,
            },
        )
        if not mensaje_created:
            continue
        creados += 1

        mensaje_recibido.send(
            sender=Mensaje,
            mensaje=mensaje,
            contacto=contacto,
            canal=canal,
            contacto_nuevo=contacto_created,
        )

    return creados
