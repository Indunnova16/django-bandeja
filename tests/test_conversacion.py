"""Tests del modelo Conversacion + integración con intake + outbound."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model

from bandeja.channels.base import InboundMessage
from bandeja.models import (
    BandejaAgentProfile,
    Canal,
    Contacto,
    Conversacion,
    Mensaje,
)
from bandeja.services.intake import process_inbound
from bandeja.signals import conversacion_creada


@pytest.fixture
def adapter():
    a = MagicMock()
    a.slug = "principal"
    a.config = {"display_name": "Test"}
    canal, _ = Canal.objects.get_or_create(
        slug="principal", defaults={"tipo": "whatsapp", "display_name": "Test"},
    )
    a.resolver_canal = MagicMock(return_value=canal)
    return a


def _inbound(external_id="wamid.1", **kw):
    base = dict(
        sender_id="573001112233",
        sender_name="X",
        timestamp=datetime(2026, 5, 12, 10, 0, tzinfo=dt_timezone.utc),
        tipo_contenido="texto",
        contenido="hola",
        external_id=external_id,
        canal_metadata={"phone_number_id": "1234"},
    )
    base.update(kw)
    return InboundMessage(**base)


@pytest.fixture
def agente_activo():
    User = get_user_model()
    u = User.objects.create_user(username="ana", first_name="Ana")
    BandejaAgentProfile.objects.create(user=u, activo=True)
    return u


@pytest.mark.django_db
def test_primer_mensaje_crea_conversacion(adapter):
    process_inbound(adapter, [_inbound()])
    assert Conversacion.objects.count() == 1
    conv = Conversacion.objects.first()
    assert conv.estado == "abierta"
    assert conv.mensajes.count() == 1


@pytest.mark.django_db
def test_segundo_mensaje_reusa_conversacion_abierta(adapter):
    process_inbound(adapter, [_inbound(external_id="wamid.1")])
    process_inbound(adapter, [_inbound(external_id="wamid.2", contenido="otro")])
    assert Conversacion.objects.count() == 1
    assert Mensaje.objects.count() == 2


@pytest.mark.django_db
def test_conversacion_resuelta_no_se_reusa(adapter):
    process_inbound(adapter, [_inbound(external_id="wamid.1")])
    conv = Conversacion.objects.first()
    conv.estado = "resuelta"
    conv.save()

    process_inbound(adapter, [_inbound(external_id="wamid.2")])
    assert Conversacion.objects.count() == 2


@pytest.mark.django_db
def test_senal_conversacion_creada_se_dispara(adapter):
    recibidos = []

    def handler(sender, conversacion, **kw):
        recibidos.append(conversacion.id)

    conversacion_creada.connect(handler)
    try:
        process_inbound(adapter, [_inbound()])
        assert len(recibidos) == 1
    finally:
        conversacion_creada.disconnect(handler)


@pytest.mark.django_db
def test_asignacion_automatica_a_agente_activo(adapter, agente_activo):
    process_inbound(adapter, [_inbound()])
    conv = Conversacion.objects.first()
    assert conv.asesor_asignado == agente_activo


@pytest.mark.django_db
def test_objeto_negocio_se_puede_setear(adapter, agente_activo):
    """Smoke test del GenericForeignKey — usamos User como dummy objeto_negocio."""
    process_inbound(adapter, [_inbound()])
    conv = Conversacion.objects.first()
    conv.objeto_negocio = agente_activo
    conv.save()
    conv.refresh_from_db()
    assert conv.objeto_negocio == agente_activo


@pytest.mark.django_db
def test_send_outbound_setea_primera_respuesta_at(monkeypatch):
    """send_outbound saliente debe marcar primera_respuesta_at una sola vez."""
    from bandeja.channels.whatsapp_cloud import WhatsAppCloudAdapter
    import bandeja.channels.whatsapp_cloud as wa_mod

    call_counter = {"n": 0}

    class FakeResp:
        def __init__(self, n):
            self.n = n
        def raise_for_status(self):
            pass
        def json(self):
            return {"messages": [{"id": f"wamid.fake-{self.n}"}]}

    def fake_post(*a, **kw):
        call_counter["n"] += 1
        return FakeResp(call_counter["n"])

    monkeypatch.setattr(wa_mod.requests, "post", fake_post)

    canal, _ = Canal.objects.get_or_create(
        slug="principal",
        defaults={"tipo": "whatsapp", "display_name": "T", "phone_number_id": "abc"},
    )
    contacto = Contacto.objects.create(wa_phone="573009998887", nombre="Carlos")
    conv = Conversacion.objects.create(contacto=contacto, canal=canal)
    assert conv.primera_respuesta_at is None

    a = WhatsAppCloudAdapter(slug="principal", config={"phone_number_id": "abc", "display_name": "T"})
    a.send_outbound(contacto, "respuesta 1", conversacion=conv)
    conv.refresh_from_db()
    primera = conv.primera_respuesta_at
    assert primera is not None

    # Segundo envío no debe modificar primera_respuesta_at
    a.send_outbound(contacto, "respuesta 2", conversacion=conv)
    conv.refresh_from_db()
    assert conv.primera_respuesta_at == primera


@pytest.mark.django_db
def test_send_outbound_nota_privada_no_llama_meta(monkeypatch):
    from bandeja.channels.whatsapp_cloud import WhatsAppCloudAdapter
    import bandeja.channels.whatsapp_cloud as wa_mod

    called = {"count": 0}

    def fake_post(*args, **kwargs):
        called["count"] += 1
        raise AssertionError("No debió llamar a Meta para nota privada")

    monkeypatch.setattr(wa_mod.requests, "post", fake_post)

    canal, _ = Canal.objects.get_or_create(
        slug="principal", defaults={"tipo": "whatsapp", "display_name": "T"},
    )
    contacto = Contacto.objects.create(wa_phone="573009990001", nombre="Y")
    conv = Conversacion.objects.create(contacto=contacto, canal=canal)

    a = WhatsAppCloudAdapter(slug="principal", config={"display_name": "T"})
    a.send_outbound(contacto, "interno", es_nota_privada=True, conversacion=conv)

    assert called["count"] == 0
    msg = Mensaje.objects.get(contacto=contacto)
    assert msg.es_nota_privada is True
    assert msg.direccion == "saliente"
    # Nota privada NO debe marcar primera_respuesta_at
    conv.refresh_from_db()
    assert conv.primera_respuesta_at is None
