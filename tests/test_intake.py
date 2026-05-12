"""Tests del servicio intake: creación de Contacto + Mensaje + señales."""
from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from unittest.mock import MagicMock

import pytest
from django.dispatch import receiver

from bandeja.channels.base import InboundMessage
from bandeja.models import Canal, Contacto, Mensaje
from bandeja.services.intake import process_inbound
from bandeja.signals import mensaje_recibido


@pytest.fixture
def adapter_fake():
    adapter = MagicMock()
    adapter.slug = "principal"
    adapter.config = {"display_name": "Test"}
    canal, _ = Canal.objects.get_or_create(
        slug="principal",
        defaults={"tipo": "whatsapp", "display_name": "Test"},
    )
    adapter.resolver_canal = MagicMock(return_value=canal)
    return adapter


def _inbound(**kwargs):
    base = dict(
        sender_id="573001112233",
        sender_name="Test User",
        timestamp=datetime(2026, 5, 12, 10, 0, tzinfo=dt_timezone.utc),
        tipo_contenido="texto",
        contenido="hola",
        external_id="wamid.111",
        canal_metadata={"phone_number_id": "1234"},
    )
    base.update(kwargs)
    return InboundMessage(**base)


@pytest.mark.django_db
def test_process_inbound_crea_contacto_y_mensaje(adapter_fake):
    creados = process_inbound(adapter_fake, [_inbound()])
    assert creados == 1
    assert Contacto.objects.filter(wa_phone="573001112233").exists()
    msg = Mensaje.objects.get(wa_message_id="wamid.111")
    assert msg.direccion == "entrante"
    assert msg.contenido == "hola"


@pytest.mark.django_db
def test_process_inbound_idempotente_por_wa_message_id(adapter_fake):
    process_inbound(adapter_fake, [_inbound()])
    creados2 = process_inbound(adapter_fake, [_inbound()])
    assert creados2 == 0
    assert Mensaje.objects.count() == 1


@pytest.mark.django_db
def test_process_inbound_dispara_senal(adapter_fake):
    recibidos = []

    @receiver(mensaje_recibido)
    def _h(sender, mensaje, contacto, canal, **kw):
        recibidos.append((mensaje.id, contacto.wa_phone))

    try:
        process_inbound(adapter_fake, [_inbound()])
        assert len(recibidos) == 1
        assert recibidos[0][1] == "573001112233"
    finally:
        mensaje_recibido.disconnect(_h)


@pytest.mark.django_db
def test_process_inbound_actualiza_fechas_contacto(adapter_fake):
    t1 = datetime(2026, 5, 12, 10, 0, tzinfo=dt_timezone.utc)
    t2 = datetime(2026, 5, 12, 11, 0, tzinfo=dt_timezone.utc)
    process_inbound(adapter_fake, [_inbound(timestamp=t1)])
    process_inbound(adapter_fake, [_inbound(external_id="wamid.222", timestamp=t2)])
    c = Contacto.objects.get(wa_phone="573001112233")
    assert c.fecha_primer_mensaje == t1
    assert c.fecha_ultimo_mensaje == t2
