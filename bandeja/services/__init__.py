"""Servicios del paquete bandeja.

- intake: orquestador único de mensajes entrantes (todos los canales)
- outbound: envío saliente unificado
- channels: lookup de adapter por slug
"""
from bandeja.services.channels import get_adapter  # noqa: F401
from bandeja.services.intake import process_inbound  # noqa: F401
from bandeja.services.outbound import send_outbound  # noqa: F401

__all__ = ["get_adapter", "process_inbound", "send_outbound"]
