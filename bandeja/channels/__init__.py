"""Adapters de canales de mensajería (WhatsApp, IG, FB, email, …).

Cada canal es una subclase de `ChannelAdapter` que sabe:
- Verificar la firma del proveedor (HMAC, JWT, …)
- Parsear el payload entrante a `InboundMessage` normalizado
- Enviar mensajes salientes (POST a la API del proveedor)

El paquete despacha al adapter correcto leyendo `slug` del URL
`/bandeja/webhook/<slug>/` y consultando `settings.BANDEJA_CHANNELS`.
"""
from bandeja.channels.base import ChannelAdapter, InboundMessage  # noqa: F401

__all__ = ["ChannelAdapter", "InboundMessage"]
