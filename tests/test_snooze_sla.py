"""Tests de snooze command + servicio SLA."""
from __future__ import annotations

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from bandeja.models import Canal, Contacto, Conversacion
from bandeja.services.sla import (
    conversaciones_en_riesgo,
    metricas_sla,
    sla_status,
)


@pytest.fixture
def canal():
    c, _ = Canal.objects.get_or_create(
        slug="principal", defaults={"tipo": "whatsapp", "display_name": "T"},
    )
    return c


@pytest.fixture
def contacto():
    return Contacto.objects.create(wa_phone="573000001111", nombre="X")


@pytest.mark.django_db
def test_despertar_pospuestos_vencidos(canal, contacto):
    ahora = timezone.now()
    vencida = Conversacion.objects.create(
        contacto=contacto, canal=canal,
        estado="pospuesta", pospuesta_hasta=ahora - timedelta(minutes=5),
    )
    futura = Conversacion.objects.create(
        contacto=contacto, canal=canal,
        estado="pospuesta", pospuesta_hasta=ahora + timedelta(hours=1),
    )
    out = StringIO()
    call_command("bandeja_despertar_pospuestos", stdout=out)
    vencida.refresh_from_db()
    futura.refresh_from_db()
    assert vencida.estado == "abierta"
    assert vencida.pospuesta_hasta is None
    assert futura.estado == "pospuesta"
    assert "1" in out.getvalue()


@pytest.mark.django_db
def test_sla_no_respondida_en_riesgo(canal, contacto, settings):
    settings.BANDEJA_SLA_PRIMERA_RESPUESTA_MIN = 15
    # Conversación abierta hace 20 min sin respuesta → en riesgo
    conv = Conversacion.objects.create(contacto=contacto, canal=canal)
    Conversacion.objects.filter(pk=conv.pk).update(
        fecha_apertura=timezone.now() - timedelta(minutes=20)
    )
    conv.refresh_from_db()

    status = sla_status(conv)
    assert status["respondida"] is False
    assert status["ok"] is False

    riesgo = list(conversaciones_en_riesgo())
    assert conv in riesgo


@pytest.mark.django_db
def test_sla_respondida_dentro_ventana(canal, contacto, settings):
    settings.BANDEJA_SLA_PRIMERA_RESPUESTA_MIN = 15
    ahora = timezone.now()
    conv = Conversacion.objects.create(contacto=contacto, canal=canal)
    Conversacion.objects.filter(pk=conv.pk).update(
        fecha_apertura=ahora - timedelta(minutes=10),
        primera_respuesta_at=ahora - timedelta(minutes=5),
    )
    conv.refresh_from_db()

    status = sla_status(conv)
    assert status["respondida"] is True
    assert status["ok"] is True


@pytest.mark.django_db
def test_metricas_sla_calcula_pct(canal, contacto, settings):
    settings.BANDEJA_SLA_PRIMERA_RESPUESTA_MIN = 15
    desde = timezone.now() - timedelta(hours=2)
    hasta = timezone.now() + timedelta(hours=1)

    # 3 conversaciones: 2 en SLA, 1 fuera
    for delta_resp in (5, 10, 30):
        conv = Conversacion.objects.create(contacto=contacto, canal=canal)
        Conversacion.objects.filter(pk=conv.pk).update(
            fecha_apertura=timezone.now() - timedelta(minutes=60),
            primera_respuesta_at=timezone.now() - timedelta(minutes=60 - delta_resp),
        )

    m = metricas_sla(desde, hasta)
    assert m["total"] == 3
    assert m["respondidas"] == 3
    assert m["en_sla"] == 2
    assert m["pct_en_sla"] == 66.7
