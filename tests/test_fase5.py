"""Tests Fase 5: menciones, reportes asesoras, merge contactos."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from bandeja.models import (
    BandejaAgentProfile,
    Canal,
    Contacto,
    ContactoEtiqueta,
    Conversacion,
    Etiqueta,
    Mencion,
    Mensaje,
)
from bandeja.services.menciones import parsear_menciones
from bandeja.services.merge import merge_contactos
from bandeja.services.reportes import reporte_asesoras


@pytest.fixture
def canal():
    c, _ = Canal.objects.get_or_create(
        slug="principal", defaults={"tipo": "whatsapp", "display_name": "T"},
    )
    return c


# ---------- Menciones ----------

@pytest.mark.django_db
def test_parsear_menciones_detecta_usuarios_existentes(canal):
    User = get_user_model()
    User.objects.create_user(username="sandra", is_active=True)
    User.objects.create_user(username="claudia", is_active=True)
    contacto = Contacto.objects.create(wa_phone="573000000001", nombre="X")
    conv = Conversacion.objects.create(contacto=contacto, canal=canal)
    msg = Mensaje.objects.create(
        contacto=contacto, canal=canal, conversacion=conv,
        direccion="saliente", contenido="@sandra revisa esto plis, @claudia FYI",
        wa_message_id="local-nota-1", timestamp=timezone.now(),
        es_nota_privada=True,
    )
    creadas = parsear_menciones(msg)
    assert len(creadas) == 2
    assert set(m.mencionado.username for m in creadas) == {"sandra", "claudia"}


@pytest.mark.django_db
def test_parsear_menciones_ignora_usuarios_inexistentes(canal):
    User = get_user_model()
    User.objects.create_user(username="sandra", is_active=True)
    contacto = Contacto.objects.create(wa_phone="573000000002", nombre="Y")
    conv = Conversacion.objects.create(contacto=contacto, canal=canal)
    msg = Mensaje.objects.create(
        contacto=contacto, canal=canal, conversacion=conv,
        direccion="saliente", contenido="@sandra y @nadie",
        wa_message_id="local-nota-2", timestamp=timezone.now(),
        es_nota_privada=True,
    )
    creadas = parsear_menciones(msg)
    assert [m.mencionado.username for m in creadas] == ["sandra"]


@pytest.mark.django_db
def test_parsear_menciones_no_procesa_mensajes_publicos(canal):
    User = get_user_model()
    User.objects.create_user(username="sandra", is_active=True)
    contacto = Contacto.objects.create(wa_phone="573000000003", nombre="Z")
    conv = Conversacion.objects.create(contacto=contacto, canal=canal)
    msg = Mensaje.objects.create(
        contacto=contacto, canal=canal, conversacion=conv,
        direccion="saliente", contenido="@sandra deberíamos atender pronto",
        wa_message_id="local-msg-3", timestamp=timezone.now(),
        es_nota_privada=False,  # mensaje público
    )
    assert parsear_menciones(msg) == []
    assert Mencion.objects.count() == 0


# ---------- Reportes ----------

@pytest.mark.django_db
def test_reporte_asesoras_calcula_metricas(canal):
    User = get_user_model()
    ana = User.objects.create_user(username="ana")
    BandejaAgentProfile.objects.create(user=ana)
    bea = User.objects.create_user(username="bea")
    BandejaAgentProfile.objects.create(user=bea)

    ahora = timezone.now()
    contacto = Contacto.objects.create(wa_phone="573000000010", nombre="C")
    c1 = Conversacion.objects.create(
        contacto=contacto, canal=canal,
        asesor_asignado=ana, estado="resuelta",
    )
    Conversacion.objects.filter(pk=c1.pk).update(
        fecha_apertura=ahora - timedelta(minutes=30),
        primera_respuesta_at=ahora - timedelta(minutes=25),
    )
    c2 = Conversacion.objects.create(
        contacto=contacto, canal=canal, asesor_asignado=ana,
    )
    Conversacion.objects.filter(pk=c2.pk).update(
        fecha_apertura=ahora - timedelta(minutes=15),
        primera_respuesta_at=ahora - timedelta(minutes=10),
    )
    Mensaje.objects.create(
        contacto=contacto, canal=canal, conversacion=c1,
        direccion="saliente", enviado_por=ana, contenido="r1",
        wa_message_id="local-r-1", timestamp=ahora,
    )

    reporte = reporte_asesoras(ahora - timedelta(hours=1), ahora + timedelta(minutes=1))
    by_user = {r["username"]: r for r in reporte}
    assert by_user["ana"]["conversaciones_abiertas_en_rango"] == 2
    assert by_user["ana"]["conversaciones_resueltas"] == 1
    assert by_user["ana"]["mensajes_salientes"] == 1
    # Tiempo medio: (5min + 5min) / 2 = 300s
    assert 290 < by_user["ana"]["tiempo_medio_primera_respuesta_seg"] < 310
    assert by_user["bea"]["conversaciones_abiertas_en_rango"] == 0


# ---------- Merge ----------

@pytest.mark.django_db
def test_merge_contactos_reasigna_todo(canal):
    User = get_user_model()
    autor = User.objects.create_user(username="autor")

    origen = Contacto.objects.create(wa_phone="573009990001", nombre="Carlos viejo")
    destino = Contacto.objects.create(wa_phone="573009990002", nombre="Carlos nuevo")

    etq = Etiqueta.objects.create(slug="vip", nombre="VIP", activa=True)
    ContactoEtiqueta.objects.create(contacto=origen, etiqueta=etq)

    c1 = Conversacion.objects.create(contacto=origen, canal=canal)
    Mensaje.objects.create(
        contacto=origen, canal=canal, conversacion=c1,
        direccion="entrante", contenido="msg1",
        wa_message_id="wamid.m1", timestamp=timezone.now(),
    )

    resumen = merge_contactos(origen, destino, autor=autor)
    assert resumen["mensajes"] == 1
    assert resumen["conversaciones"] == 1
    assert resumen["etiquetas_nuevas"] == 1

    origen.refresh_from_db()
    destino.refresh_from_db()
    assert origen.fusionado_en == destino
    assert Mensaje.objects.filter(contacto=destino).count() == 1
    assert Conversacion.objects.filter(contacto=destino).count() == 1
    assert ContactoEtiqueta.objects.filter(contacto=destino, etiqueta=etq).exists()
    assert not ContactoEtiqueta.objects.filter(contacto=origen).exists()


@pytest.mark.django_db
def test_merge_contactos_mismo_id_rechaza():
    c = Contacto.objects.create(wa_phone="573000333000", nombre="X")
    with pytest.raises(ValueError, match="mismo contacto"):
        merge_contactos(c, c)


@pytest.mark.django_db
def test_merge_contactos_ya_fusionado_rechaza():
    a = Contacto.objects.create(wa_phone="1", nombre="A")
    b = Contacto.objects.create(wa_phone="2", nombre="B")
    c = Contacto.objects.create(wa_phone="3", nombre="C")
    merge_contactos(a, b)
    with pytest.raises(ValueError, match="ya fue fusionado"):
        merge_contactos(a, c)
