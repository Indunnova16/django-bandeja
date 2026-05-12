"""Tests funcionales con Django Test Client sobre las vistas de bandeja."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from bandeja.models import (
    BandejaAgentProfile,
    Canal,
    Contacto,
    Conversacion,
    Etiqueta,
    Macro,
    Mensaje,
    RespuestaGuardada,
)


@pytest.fixture
def agente():
    User = get_user_model()
    u = User.objects.create_user(username="sandra", password="x", first_name="Sandra")
    BandejaAgentProfile.objects.create(user=u, activo=True)
    return u


@pytest.fixture
def cliente_auth(agente):
    c = Client()
    c.force_login(agente)
    return c


@pytest.fixture
def canal():
    c, _ = Canal.objects.get_or_create(
        slug="principal",
        defaults={"tipo": "whatsapp", "display_name": "T", "phone_number_id": "x"},
    )
    return c


@pytest.fixture
def conv(canal, agente):
    contacto = Contacto.objects.create(wa_phone="573001112233", nombre="X")
    return Conversacion.objects.create(
        contacto=contacto, canal=canal, asesor_asignado=agente,
    )


# -------- Listado --------

@pytest.mark.django_db
def test_inbox_requires_login():
    c = Client()
    resp = c.get("/bandeja/inbox/")
    assert resp.status_code == 302
    assert "/login/" in resp.headers["Location"]


@pytest.mark.django_db
def test_inbox_lista_conversaciones(cliente_auth, conv):
    resp = cliente_auth.get("/bandeja/inbox/")
    assert resp.status_code == 200
    assert b"X" in resp.content  # nombre del contacto
    assert b"Abierta" in resp.content  # estado badge


@pytest.mark.django_db
def test_inbox_filtra_por_estado(cliente_auth, conv):
    Conversacion.objects.filter(pk=conv.pk).update(estado="resuelta")
    resp = cliente_auth.get("/bandeja/inbox/?estado=resuelta")
    assert resp.status_code == 200
    assert b"X" in resp.content

    resp_abiertas = cliente_auth.get("/bandeja/inbox/?estado=abierta")
    assert b"No hay conversaciones" in resp_abiertas.content


@pytest.mark.django_db
def test_inbox_filtra_por_etiqueta(cliente_auth, conv):
    etq = Etiqueta.objects.create(slug="vip", nombre="VIP")
    from bandeja.models import ConversacionEtiqueta
    ConversacionEtiqueta.objects.create(conversacion=conv, etiqueta=etq)
    resp = cliente_auth.get("/bandeja/inbox/?etiqueta=vip")
    assert resp.status_code == 200
    assert b"X" in resp.content


# -------- Detalle --------

@pytest.mark.django_db
def test_conversacion_detalle(cliente_auth, conv):
    Mensaje.objects.create(
        contacto=conv.contacto, canal=conv.canal, conversacion=conv,
        direccion="entrante", contenido="hola",
        wa_message_id="m1", timestamp="2026-05-12T10:00:00Z",
    )
    resp = cliente_auth.get(f"/bandeja/inbox/c/{conv.id}/")
    assert resp.status_code == 200
    assert b"hola" in resp.content


@pytest.mark.django_db
def test_conversacion_404_si_no_existe(cliente_auth):
    resp = cliente_auth.get("/bandeja/inbox/c/99999/")
    assert resp.status_code == 404


# -------- Enviar --------

@pytest.mark.django_db
def test_enviar_nota_privada_no_llama_meta(monkeypatch, cliente_auth, conv):
    """Nota privada → persiste pero NO llama HTTP a Meta."""
    import bandeja.channels.whatsapp_cloud as wa_mod
    monkeypatch.setattr(
        wa_mod.requests, "post",
        lambda *a, **kw: pytest.fail("No debió llamar a Meta"),
    )
    # Reset cache adapter por settings override
    from bandeja.services.channels import get_adapter
    get_adapter.cache_clear()

    resp = cliente_auth.post(
        f"/bandeja/inbox/c/{conv.id}/enviar/",
        {"texto": "anota esto", "nota_privada": "1"},
    )
    assert resp.status_code == 200
    msg = Mensaje.objects.get(conversacion=conv, direccion="saliente")
    assert msg.es_nota_privada is True
    assert msg.contenido == "anota esto"


@pytest.mark.django_db
def test_enviar_texto_vacio_400(cliente_auth, conv):
    resp = cliente_auth.post(
        f"/bandeja/inbox/c/{conv.id}/enviar/",
        {"texto": "   ", "nota_privada": "0"},
    )
    assert resp.status_code == 400


# -------- Estado --------

@pytest.mark.django_db
def test_cambiar_estado_a_resuelta(cliente_auth, conv):
    resp = cliente_auth.post(
        f"/bandeja/inbox/c/{conv.id}/estado/",
        {"estado": "resuelta"},
    )
    assert resp.status_code == 200
    conv.refresh_from_db()
    assert conv.estado == "resuelta"
    assert conv.fecha_resolucion is not None


@pytest.mark.django_db
def test_cambiar_estado_invalido_400(cliente_auth, conv):
    resp = cliente_auth.post(
        f"/bandeja/inbox/c/{conv.id}/estado/",
        {"estado": "invalido"},
    )
    assert resp.status_code == 400


# -------- Snooze --------

@pytest.mark.django_db
def test_posponer_preset_1h(cliente_auth, conv):
    resp = cliente_auth.post(
        f"/bandeja/inbox/c/{conv.id}/posponer/",
        {"preset": "1h"},
    )
    assert resp.status_code == 200
    conv.refresh_from_db()
    assert conv.estado == "pospuesta"
    assert conv.pospuesta_hasta is not None


# -------- Etiquetas --------

@pytest.mark.django_db
def test_toggle_etiqueta_aplica_y_quita(cliente_auth, conv):
    Etiqueta.objects.create(slug="vip", nombre="VIP", color="#ff0000")
    # Aplicar
    resp1 = cliente_auth.post(
        f"/bandeja/inbox/c/{conv.id}/etiqueta/", {"slug": "vip"},
    )
    assert resp1.status_code == 200
    from bandeja.models import ConversacionEtiqueta
    assert ConversacionEtiqueta.objects.filter(conversacion=conv).count() == 1
    # Toggle off
    resp2 = cliente_auth.post(
        f"/bandeja/inbox/c/{conv.id}/etiqueta/", {"slug": "vip"},
    )
    assert resp2.status_code == 200
    assert ConversacionEtiqueta.objects.filter(conversacion=conv).count() == 0


@pytest.mark.django_db
def test_toggle_etiqueta_inexistente_404(cliente_auth, conv):
    resp = cliente_auth.post(
        f"/bandeja/inbox/c/{conv.id}/etiqueta/", {"slug": "no-existe"},
    )
    assert resp.status_code == 404


# -------- Macros --------

@pytest.mark.django_db
def test_aplicar_macro(cliente_auth, conv):
    Etiqueta.objects.create(slug="resuelto", nombre="Resuelto", activa=True)
    macro = Macro.objects.create(
        slug="cerrar-rapido", nombre="Cerrar rápido", activa=True,
        pasos=[
            {"action": "agregar_etiqueta", "args": {"slug": "resuelto"}},
            {"action": "cerrar_conversacion"},
        ],
    )
    resp = cliente_auth.post(
        f"/bandeja/inbox/c/{conv.id}/macros/{macro.id}/aplicar/",
    )
    assert resp.status_code == 200
    assert b"aplicada" in resp.content.lower()
    conv.refresh_from_db()
    assert conv.estado == "resuelta"


# -------- CRUD etiquetas --------

@pytest.mark.django_db
def test_etiquetas_create_via_post(cliente_auth):
    resp = cliente_auth.post(
        "/bandeja/etiquetas/",
        {"slug": "mayorista", "nombre": "Mayorista", "color": "#10b981"},
    )
    assert resp.status_code == 200
    assert Etiqueta.objects.filter(slug="mayorista").exists()


# -------- Respuestas guardadas --------

@pytest.mark.django_db
def test_respuestas_buscar(cliente_auth):
    RespuestaGuardada.objects.create(
        slug="medidas", titulo="Pregunta medidas", cuerpo="¿Qué medidas necesitas?",
        activa=True,
    )
    resp = cliente_auth.get("/bandeja/respuestas/buscar/?q=med")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["slug"] == "medidas"
