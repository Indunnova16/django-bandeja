"""Tests del WhatsAppCloudAdapter: firma HMAC, parseo de payload, lookup canal."""
from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock

import pytest

from bandeja.channels.whatsapp_cloud import WhatsAppCloudAdapter

CONFIG = {
    "phone_number_id": "1234567890",
    "verify_token": "token-de-prueba",
    "app_secret": "secret-de-prueba",
    "access_token": "access-token-de-prueba",
    "display_name": "Test Channel",
}


def _make_request(body: bytes, signature: str | None = None, get_params: dict | None = None):
    req = MagicMock()
    req.body = body
    req.headers = {}
    if signature:
        req.headers["X-Hub-Signature-256"] = signature
    req.GET = get_params or {}
    return req


@pytest.fixture
def adapter():
    return WhatsAppCloudAdapter(slug="principal", config=CONFIG)


class _FakeGET(dict):
    """dict que soporta .get igual que QueryDict."""


def _req_with_get(params: dict):
    req = MagicMock()
    req.GET = _FakeGET(params)
    return req


def test_verify_subscription_ok(adapter):
    req = _req_with_get({
        "hub.mode": "subscribe",
        "hub.verify_token": "token-de-prueba",
        "hub.challenge": "ch4ll3ng3",
    })
    assert adapter.verify_subscription(req) == "ch4ll3ng3"


def test_verify_subscription_bad_token(adapter):
    req = _req_with_get({"hub.mode": "subscribe", "hub.verify_token": "MAL", "hub.challenge": "x"})
    assert adapter.verify_subscription(req) is None


def test_verify_signature_ok(adapter):
    body = b'{"hello":"world"}'
    expected = hmac.new(CONFIG["app_secret"].encode(), body, hashlib.sha256).hexdigest()
    req = _make_request(body, signature=f"sha256={expected}")
    assert adapter.verify_signature(req) is True


def test_verify_signature_bad(adapter):
    req = _make_request(b'{}', signature="sha256=deadbeef")
    assert adapter.verify_signature(req) is False


def test_verify_signature_missing_header(adapter):
    req = _make_request(b'{}', signature=None)
    assert adapter.verify_signature(req) is False


def test_verify_signature_no_secret():
    a = WhatsAppCloudAdapter(slug="x", config={"app_secret": ""})
    req = _make_request(b'{}', signature="sha256=anything")
    assert a.verify_signature(req) is False


def test_parse_inbound_text_message(adapter):
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {"phone_number_id": "1234567890"},
                    "contacts": [{"wa_id": "573001234567", "profile": {"name": "Carlos"}}],
                    "messages": [{
                        "id": "wamid.ABC",
                        "from": "573001234567",
                        "timestamp": "1715000000",
                        "type": "text",
                        "text": {"body": "Hola, quiero info"},
                    }],
                }
            }]
        }]
    }
    req = _make_request(json.dumps(payload).encode())
    inbounds = adapter.parse_inbound(req)
    assert len(inbounds) == 1
    msg = inbounds[0]
    assert msg.sender_id == "573001234567"
    assert msg.sender_name == "Carlos"
    assert msg.tipo_contenido == "texto"
    assert msg.contenido == "Hola, quiero info"
    assert msg.external_id == "wamid.ABC"
    assert msg.canal_metadata["phone_number_id"] == "1234567890"


def test_parse_inbound_image_with_caption(adapter):
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {"phone_number_id": "1234567890"},
                    "contacts": [{"wa_id": "573001234567", "profile": {"name": ""}}],
                    "messages": [{
                        "id": "wamid.IMG",
                        "from": "573001234567",
                        "timestamp": "1715000000",
                        "type": "image",
                        "image": {"caption": "mira esto"},
                    }],
                }
            }]
        }]
    }
    req = _make_request(json.dumps(payload).encode())
    inbounds = adapter.parse_inbound(req)
    assert len(inbounds) == 1
    assert inbounds[0].tipo_contenido == "imagen"
    assert inbounds[0].contenido == "mira esto"


def test_parse_inbound_no_messages_returns_empty(adapter):
    payload = {"entry": [{"changes": [{"value": {"statuses": []}}]}]}
    req = _make_request(json.dumps(payload).encode())
    assert adapter.parse_inbound(req) == []


def test_parse_inbound_bad_json_returns_empty(adapter):
    req = _make_request(b"not-json")
    assert adapter.parse_inbound(req) == []
