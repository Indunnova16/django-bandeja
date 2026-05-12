"""Tests del sistema de macros: registry, ejecutor, acciones built-in."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from bandeja.macros import ejecutar_macro, register_action, MacroError
from bandeja.models import (
    Canal,
    Contacto,
    Conversacion,
    ConversacionEtiqueta,
    Etiqueta,
    Macro,
)


@pytest.fixture
def conversacion_demo():
    canal, _ = Canal.objects.get_or_create(
        slug="principal", defaults={"tipo": "whatsapp", "display_name": "T"},
    )
    contacto = Contacto.objects.create(wa_phone="573001112233", nombre="X")
    return Conversacion.objects.create(contacto=contacto, canal=canal)


@pytest.fixture
def autor():
    User = get_user_model()
    return User.objects.create_user(username="agente", is_active=True)


@pytest.mark.django_db
def test_macro_agregar_etiqueta(conversacion_demo, autor):
    Etiqueta.objects.create(slug="perdida", nombre="Perdida", activa=True)
    macro = Macro.objects.create(
        slug="cierre-perdida",
        nombre="Cierre perdida",
        pasos=[{"action": "agregar_etiqueta", "args": {"slug": "perdida"}}],
    )
    ej = ejecutar_macro(macro, conversacion_demo, autor=autor)
    assert ej.exitoso is True
    assert ConversacionEtiqueta.objects.filter(
        conversacion=conversacion_demo, etiqueta__slug="perdida",
    ).exists()


@pytest.mark.django_db
def test_macro_cerrar_conversacion(conversacion_demo, autor):
    macro = Macro.objects.create(
        slug="cerrar", nombre="Cerrar",
        pasos=[{"action": "cerrar_conversacion"}],
    )
    ejecutar_macro(macro, conversacion_demo, autor=autor)
    conversacion_demo.refresh_from_db()
    assert conversacion_demo.estado == "resuelta"
    assert conversacion_demo.fecha_resolucion is not None


@pytest.mark.django_db
def test_macro_etiqueta_inexistente_marca_fallo(conversacion_demo, autor):
    macro = Macro.objects.create(
        slug="bad", nombre="Bad",
        pasos=[{"action": "agregar_etiqueta", "args": {"slug": "no-existe"}}],
    )
    ej = ejecutar_macro(macro, conversacion_demo, autor=autor)
    assert ej.exitoso is False
    assert "no existe" in ej.error.lower()


@pytest.mark.django_db
def test_macro_secuencia_falla_para_en_primer_error(conversacion_demo, autor):
    Etiqueta.objects.create(slug="bueno", nombre="Bueno", activa=True)
    macro = Macro.objects.create(
        slug="multi", nombre="Multi",
        pasos=[
            {"action": "agregar_etiqueta", "args": {"slug": "bueno"}},
            {"action": "agregar_etiqueta", "args": {"slug": "no-existe"}},
            {"action": "cerrar_conversacion"},
        ],
    )
    ej = ejecutar_macro(macro, conversacion_demo, autor=autor)
    assert ej.exitoso is False
    # Solo el primer paso ejecutó OK
    assert len(ej.pasos_ejecutados) == 1
    # Conversación NO debe estar cerrada (paso 3 no corrió)
    conversacion_demo.refresh_from_db()
    assert conversacion_demo.estado != "resuelta"


@pytest.mark.django_db
def test_register_action_custom(conversacion_demo, autor):
    """Patrón huésped: registrar acción específica del dominio."""
    estado_capturado = {}

    @register_action("test_custom_action_xyz")
    def custom_action(ejecucion, *, valor, **_):
        estado_capturado["conv_id"] = ejecucion.conversacion.id
        estado_capturado["valor"] = valor

    macro = Macro.objects.create(
        slug="custom", nombre="C",
        pasos=[{"action": "test_custom_action_xyz", "args": {"valor": 42}}],
    )
    ej = ejecutar_macro(macro, conversacion_demo, autor=autor)
    assert ej.exitoso
    assert estado_capturado["valor"] == 42
    assert estado_capturado["conv_id"] == conversacion_demo.id
