"""Contrato de los adapters de canal."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class InboundMessage:
    """Mensaje entrante normalizado, agnóstico del canal."""

    sender_id: str  # número E.164 / IG user id / email / …
    sender_name: str = ""
    timestamp: datetime | None = None
    tipo_contenido: str = "texto"
    contenido: str = ""
    external_id: str = ""  # id del proveedor (wa_message_id, etc.)
    canal_metadata: dict[str, Any] = field(default_factory=dict)


class ChannelAdapter(ABC):
    """Adapter de un canal de mensajería.

    El adapter recibe su configuración en `__init__` desde
    `settings.BANDEJA_CHANNELS[slug]`. Es responsable de:
    - `verify_signature` — validar autenticidad del webhook entrante
    - `parse_inbound` — convertir el payload del proveedor a `InboundMessage`
    - `send_outbound` — enviar un mensaje saliente vía la API del proveedor
    """

    slug: str = ""

    def __init__(self, slug: str, config: dict):
        self.slug = slug
        self.config = config

    @abstractmethod
    def verify_signature(self, request) -> bool: ...

    @abstractmethod
    def verify_subscription(self, request) -> str | None:
        """Para GET verifications (webhook setup). Devuelve el challenge si OK."""

    @abstractmethod
    def parse_inbound(self, request) -> list[InboundMessage]: ...

    @abstractmethod
    def send_outbound(self, contacto, texto: str, **kwargs) -> dict: ...
