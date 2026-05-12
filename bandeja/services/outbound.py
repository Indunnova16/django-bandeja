"""Envío saliente unificado."""
from __future__ import annotations

import logging

from bandeja.services.channels import get_adapter
from bandeja.signals import mensaje_enviado

logger = logging.getLogger("bandeja.services.outbound")


def send_outbound(
    canal_slug: str,
    contacto,
    texto: str,
    usuario=None,
    es_nota_privada: bool = False,
    **kwargs,
) -> dict:
    """Envía un mensaje saliente vía el adapter del canal indicado.

    Si `es_nota_privada=True`, solo persiste el mensaje localmente sin
    llamar al adapter (el flag está reservado para Fase 3, donde se
    agrega `Mensaje.es_nota_privada`).
    """
    adapter = get_adapter(canal_slug)
    result = adapter.send_outbound(
        contacto,
        texto,
        usuario=usuario,
        es_nota_privada=es_nota_privada,
        **kwargs,
    )
    # mensaje_enviado se dispara sin instancia para no acoplar a UI
    mensaje_enviado.send(
        sender=type(adapter),
        contacto=contacto,
        canal_slug=canal_slug,
        texto=texto,
        usuario=usuario,
        result=result,
    )
    return result
