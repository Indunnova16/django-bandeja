"""Webhook view genérico parametrizado por slug de canal."""
from __future__ import annotations

import logging

from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from bandeja.services.channels import get_adapter
from bandeja.services.intake import process_inbound

logger = logging.getLogger("bandeja.views.webhook")


@method_decorator(csrf_exempt, name="dispatch")
class WebhookView(View):
    """Recibe webhooks de cualquier canal configurado.

    URL: `/bandeja/webhook/<channel_slug>/`

    - GET: valida la suscripción del webhook (challenge handshake).
    - POST: valida firma, parsea, persiste mensajes y devuelve 200.
    """

    http_method_names = ["get", "post"]

    def get(self, request, channel_slug: str):
        adapter = get_adapter(channel_slug)
        challenge = adapter.verify_subscription(request)
        if challenge is not None:
            logger.info("Webhook %s verificado", channel_slug)
            return HttpResponse(challenge, content_type="text/plain")
        return JsonResponse({"error": "invalid token"}, status=403)

    def post(self, request, channel_slug: str):
        adapter = get_adapter(channel_slug)
        if not adapter.verify_signature(request):
            logger.warning("Firma inválida en webhook %s", channel_slug)
            return JsonResponse({"error": "invalid signature"}, status=403)

        try:
            inbounds = adapter.parse_inbound(request)
            creados = process_inbound(adapter, inbounds)
            logger.info("Webhook %s: %s mensajes nuevos", channel_slug, creados)
        except Exception:  # noqa: BLE001
            logger.exception("Error procesando webhook %s", channel_slug)

        # Meta exige 200 incluso ante errores internos para no reintentar.
        return JsonResponse({"status": "received"}, status=200)
