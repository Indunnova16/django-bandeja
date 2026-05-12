"""Adapter de WhatsApp Cloud API (Meta)."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone as dt_timezone

import requests
from django.utils import timezone

from bandeja.channels.base import ChannelAdapter, InboundMessage
from bandeja.models import Canal, Mensaje

logger = logging.getLogger("bandeja.channels.whatsapp_cloud")

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0"

_TIPO_CONTENIDO_MAP = {
    "text": "texto",
    "audio": "audio",
    "voice": "audio",
    "image": "imagen",
    "document": "documento",
    "sticker": "sticker",
    "location": "ubicacion",
}


def _ts_to_aware(timestamp_str: str) -> datetime:
    try:
        return datetime.fromtimestamp(int(timestamp_str), tz=dt_timezone.utc)
    except (TypeError, ValueError):
        return timezone.now()


class WhatsAppCloudAdapter(ChannelAdapter):
    """Adapter para WhatsApp Cloud API (Meta).

    Configuración esperada en `settings.BANDEJA_CHANNELS[slug]`:
        adapter:         dotted path a esta clase
        phone_number_id: ID del número WhatsApp
        verify_token:    token de verificación del webhook (GET)
        app_secret:      secreto de la app Meta para validar HMAC
        access_token:    token bearer para enviar mensajes
        display_name:    nombre legible del número
    """

    def verify_subscription(self, request) -> str | None:
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge", "")
        if mode == "subscribe" and token == self.config.get("verify_token", ""):
            return challenge
        return None

    def verify_signature(self, request) -> bool:
        secret = self.config.get("app_secret", "")
        if not secret:
            logger.warning(
                "app_secret vacío para canal %s — rechazando webhook", self.slug
            )
            return False
        signature_header = request.headers.get("X-Hub-Signature-256", "")
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header[7:])

    def parse_inbound(self, request) -> list[InboundMessage]:
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return []

        salida: list[InboundMessage] = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "messages" not in value:
                    continue
                profiles = {
                    c["wa_id"]: c.get("profile", {}).get("name", "")
                    for c in value.get("contacts", [])
                }
                phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
                for msg in value["messages"]:
                    tipo_meta = msg.get("type", "text")
                    contenido = ""
                    if tipo_meta == "text":
                        contenido = msg.get("text", {}).get("body", "")
                    elif tipo_meta in ("image", "document", "audio", "voice", "sticker"):
                        contenido = msg.get(tipo_meta, {}).get("caption", "") or f"[{tipo_meta}]"
                    elif tipo_meta == "location":
                        loc = msg.get("location", {})
                        contenido = f"[ubicación] {loc.get('latitude')},{loc.get('longitude')}"
                    salida.append(InboundMessage(
                        sender_id=msg["from"],
                        sender_name=profiles.get(msg["from"], ""),
                        timestamp=_ts_to_aware(msg.get("timestamp", "")),
                        tipo_contenido=_TIPO_CONTENIDO_MAP.get(tipo_meta, "otro"),
                        contenido=contenido,
                        external_id=msg["id"],
                        canal_metadata={"phone_number_id": phone_number_id},
                    ))
        return salida

    def resolver_canal(self, phone_number_id: str = "") -> Canal:
        """Devuelve (creando si hace falta) el modelo `Canal` correspondiente."""
        target_phone_id = phone_number_id or self.config.get("phone_number_id", "")
        canal, _ = Canal.objects.get_or_create(
            slug=self.slug,
            defaults={
                "tipo": "whatsapp",
                "phone_number_id": target_phone_id,
                "display_name": self.config.get("display_name", self.slug),
            },
        )
        # Si cambió el phone_number_id en config, sincronizar
        if target_phone_id and canal.phone_number_id != target_phone_id:
            canal.phone_number_id = target_phone_id
            canal.save(update_fields=["phone_number_id", "updated_at"])
        return canal

    def send_outbound(
        self,
        contacto,
        texto: str,
        usuario=None,
        es_nota_privada: bool = False,
        **kwargs,
    ) -> dict:
        """Envía un mensaje saliente. Persiste `Mensaje` siempre, llama a Meta
        solo si NO es nota privada."""
        canal = self.resolver_canal()

        wa_id = ""
        result: dict = {}
        if not es_nota_privada:
            url = f"{WHATSAPP_API_URL}/{canal.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.config.get('access_token', '')}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": contacto.wa_phone,
                "type": "text",
                "text": {"body": texto[:4096]},
            }
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            wa_id = (result.get("messages") or [{}])[0].get("id", "")

        if not wa_id:
            wa_id = f"local-{timezone.now().timestamp()}"

        Mensaje.objects.create(
            contacto=contacto,
            canal=canal,
            direccion="saliente",
            tipo_contenido="texto",
            contenido=texto,
            wa_message_id=wa_id,
            enviado_por=usuario if (usuario and getattr(usuario, "is_authenticated", False)) else None,
            timestamp=timezone.now(),
        )
        contacto.fecha_ultimo_mensaje = timezone.now()
        contacto.save(update_fields=["fecha_ultimo_mensaje", "updated_at"])
        return result
