"""Vistas de la bandeja UI — operan sobre Conversacion, no Oportunidad.

Reemplaza a `apps/inbox/views.py` del huésped. La extensión por host se hace
vía:
- override de templates en `<host>/templates/bandeja/...`
- side-panel del objeto_negocio se renderiza vía template tag
  `{% bandeja_objeto_negocio_panel conversacion %}` que el host sobrescribe.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Prefetch, Subquery
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from bandeja.macros import ejecutar_macro
from bandeja.models import (
    Conversacion,
    ConversacionEtiqueta,
    Etiqueta,
    Macro,
    Mensaje,
    RespuestaGuardada,
)
from bandeja.services.outbound import send_outbound
from bandeja.services.menciones import parsear_menciones
from bandeja.services.sla import sla_status
from bandeja.signals import conversacion_resuelta

logger = logging.getLogger("bandeja.views.inbox")

ESTADOS_TABS = [
    ("todas", "Todas"),
    ("abierta", "Abiertas"),
    ("pendiente", "Pendientes"),
    ("pospuesta", "Pospuestas"),
    ("resuelta", "Resueltas"),
]


def _filtrar_conversaciones(estado: str):
    qs = (
        Conversacion.objects
        .select_related("contacto", "canal", "asesor_asignado", "asesor_asignado__bandeja_profile")
        .prefetch_related("etiquetas_rel__etiqueta")
        .order_by("-fecha_ultimo_mensaje", "-fecha_apertura")
    )
    if estado and estado != "todas":
        qs = qs.filter(estado=estado)
    ultimo = (
        Mensaje.objects
        .filter(conversacion=OuterRef("pk"), es_nota_privada=False)
        .order_by("-timestamp")
        .values("contenido")[:1]
    )
    return qs.annotate(ultimo_mensaje=Subquery(ultimo))


@login_required
def inbox(request):
    estado = request.GET.get("estado", "todas")
    etiqueta_slug = request.GET.get("etiqueta", "")

    qs = _filtrar_conversaciones(estado)
    if etiqueta_slug:
        qs = qs.filter(etiquetas_rel__etiqueta__slug=etiqueta_slug).distinct()

    conversaciones = list(qs[:200])
    # Anotar SLA en memoria (la query ya está ordenada por actividad)
    for c in conversaciones:
        c.sla = sla_status(c)

    total = Conversacion.objects.count()
    counts_por_estado = {
        e: Conversacion.objects.filter(estado=e).count()
        for e, _ in ESTADOS_TABS if e != "todas"
    }
    tabs = [
        (code, label, total if code == "todas" else counts_por_estado.get(code, 0))
        for code, label in ESTADOS_TABS
    ]
    etiquetas = Etiqueta.objects.filter(activa=True)
    context = {
        "conversaciones": conversaciones,
        "estado_actual": estado,
        "tabs": tabs,
        "etiquetas": etiquetas,
        "etiqueta_filtro": etiqueta_slug,
    }
    template = "bandeja/inbox/_lista.html" if getattr(request, "htmx", False) else "bandeja/inbox/bandeja.html"
    return render(request, template, context)


@login_required
def conversacion_view(request, conversacion_id: int):
    conv = get_object_or_404(
        Conversacion.objects.select_related(
            "contacto", "canal", "asesor_asignado", "asesor_asignado__bandeja_profile",
        ).prefetch_related("etiquetas_rel__etiqueta"),
        pk=conversacion_id,
    )
    mensajes = (
        Mensaje.objects.filter(conversacion=conv)
        .select_related("enviado_por", "enviado_por__bandeja_profile")
        .order_by("timestamp")[:500]
    )
    macros = Macro.objects.filter(activa=True)
    etiquetas_disponibles = Etiqueta.objects.filter(activa=True)
    etiquetas_aplicadas_ids = set(
        conv.etiquetas_rel.values_list("etiqueta_id", flat=True)
    )
    context = {
        "conversacion": conv,
        "mensajes": mensajes,
        "macros": macros,
        "etiquetas_disponibles": etiquetas_disponibles,
        "etiquetas_aplicadas_ids": etiquetas_aplicadas_ids,
        "sla": sla_status(conv),
        "estados": Conversacion.ESTADO_CHOICES,
    }
    return render(request, "bandeja/inbox/conversacion.html", context)


@login_required
@require_POST
def enviar(request, conversacion_id: int):
    conv = get_object_or_404(Conversacion, pk=conversacion_id)
    texto = (request.POST.get("texto") or "").strip()
    es_nota_privada = request.POST.get("nota_privada") == "1"
    if not texto:
        return JsonResponse({"error": "texto vacío"}, status=400)

    try:
        send_outbound(
            conv.canal.slug, conv.contacto, texto,
            usuario=request.user,
            es_nota_privada=es_nota_privada,
            conversacion=conv,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error enviando")
        return JsonResponse({"error": str(exc)}, status=502)

    if es_nota_privada:
        # Reparser para detectar @menciones — toma el último mensaje saliente con flag privado
        ultimo = (
            Mensaje.objects.filter(conversacion=conv, es_nota_privada=True)
            .order_by("-timestamp")
            .first()
        )
        if ultimo:
            parsear_menciones(ultimo)

    mensajes = (
        Mensaje.objects.filter(conversacion=conv)
        .select_related("enviado_por", "enviado_por__bandeja_profile")
        .order_by("timestamp")[:500]
    )
    return render(request, "bandeja/inbox/_timeline.html", {
        "mensajes": mensajes, "conversacion": conv,
    })


@login_required
@require_POST
def cambiar_estado(request, conversacion_id: int):
    """Cambia estado bandeja: abierta | pendiente | resuelta."""
    conv = get_object_or_404(Conversacion, pk=conversacion_id)
    nuevo = request.POST.get("estado", "")
    if nuevo not in dict(Conversacion.ESTADO_CHOICES):
        return HttpResponse("estado inválido", status=400)

    conv.estado = nuevo
    if nuevo == "resuelta" and not conv.fecha_resolucion:
        conv.fecha_resolucion = timezone.now()
    conv.save(update_fields=["estado", "fecha_resolucion", "updated_at"])

    if nuevo == "resuelta":
        conversacion_resuelta.send(
            sender=Conversacion, conversacion=conv, resuelta_por=request.user,
        )

    return render(request, "bandeja/inbox/_estado_badge.html", {"conversacion": conv})


@login_required
@require_POST
def posponer(request, conversacion_id: int):
    """Pospone una conversación hasta `hasta_iso` (ISO 8601) o preset."""
    conv = get_object_or_404(Conversacion, pk=conversacion_id)
    preset = request.POST.get("preset", "")
    ahora = timezone.now()
    presets = {
        "1h": ahora + timedelta(hours=1),
        "manana_9": (ahora + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0),
        "lunes_9": _proximo_lunes_9am(ahora),
    }
    if preset in presets:
        hasta = presets[preset]
    else:
        iso = request.POST.get("hasta_iso", "")
        try:
            hasta = datetime.fromisoformat(iso)
        except ValueError:
            return HttpResponse("hasta_iso inválido", status=400)

    conv.estado = "pospuesta"
    conv.pospuesta_hasta = hasta
    conv.save(update_fields=["estado", "pospuesta_hasta", "updated_at"])
    return render(request, "bandeja/inbox/_estado_badge.html", {"conversacion": conv})


@login_required
@require_POST
def aplicar_macro(request, conversacion_id: int, macro_id: int):
    conv = get_object_or_404(Conversacion, pk=conversacion_id)
    macro = get_object_or_404(Macro, pk=macro_id, activa=True)
    ej = ejecutar_macro(macro, conv, autor=request.user)
    if ej.exitoso:
        return HttpResponse(
            f"<div class='text-xs text-emerald-700'>Macro «{macro.nombre}» aplicada.</div>"
        )
    return HttpResponse(
        f"<div class='text-xs text-rose-700'>Falló: {ej.error or '?'}</div>",
        status=200,  # 200 para que HTMX intercambie el contenido
    )


@login_required
@require_POST
def toggle_etiqueta(request, conversacion_id: int):
    conv = get_object_or_404(Conversacion, pk=conversacion_id)
    slug = request.POST.get("slug", "")
    try:
        etq = Etiqueta.objects.get(slug=slug, activa=True)
    except Etiqueta.DoesNotExist:
        return HttpResponse("etiqueta inexistente", status=404)

    rel = ConversacionEtiqueta.objects.filter(conversacion=conv, etiqueta=etq).first()
    if rel:
        rel.delete()
    else:
        ConversacionEtiqueta.objects.create(
            conversacion=conv, etiqueta=etq, created_by=request.user,
        )

    aplicadas = list(
        ConversacionEtiqueta.objects.filter(conversacion=conv).values_list("etiqueta__slug", flat=True)
    )
    return render(request, "bandeja/inbox/_etiquetas_chips.html", {
        "conversacion": conv,
        "etiquetas_disponibles": Etiqueta.objects.filter(activa=True),
        "etiquetas_aplicadas_ids": set(
            ConversacionEtiqueta.objects.filter(conversacion=conv).values_list("etiqueta_id", flat=True)
        ),
        "aplicadas_slugs": aplicadas,
    })


def _proximo_lunes_9am(ahora: datetime) -> datetime:
    dias = (7 - ahora.weekday()) % 7 or 7  # próximo lunes (no hoy)
    target = ahora + timedelta(days=dias)
    return target.replace(hour=9, minute=0, second=0, microsecond=0)


# ----------- CRUD Etiquetas -----------

@login_required
def etiquetas_list(request):
    if request.method == "POST":
        slug = (request.POST.get("slug") or "").strip()
        nombre = (request.POST.get("nombre") or "").strip()
        color = (request.POST.get("color") or "#94a3b8").strip()
        if slug and nombre:
            Etiqueta.objects.get_or_create(
                slug=slug, defaults={"nombre": nombre, "color": color},
            )
    etiquetas = Etiqueta.objects.all()
    return render(request, "bandeja/etiquetas/list.html", {"etiquetas": etiquetas})


@login_required
@require_POST
def etiqueta_toggle(request, slug: str):
    etq = get_object_or_404(Etiqueta, slug=slug)
    etq.activa = not etq.activa
    etq.save(update_fields=["activa", "updated_at"])
    return HttpResponse("activa" if etq.activa else "inactiva")


# ----------- CRUD Respuestas guardadas -----------

@login_required
def respuestas_list(request):
    if request.method == "POST":
        slug = (request.POST.get("slug") or "").strip()
        titulo = (request.POST.get("titulo") or "").strip()
        cuerpo = (request.POST.get("cuerpo") or "").strip()
        if slug and titulo and cuerpo:
            RespuestaGuardada.objects.update_or_create(
                slug=slug,
                defaults={"titulo": titulo, "cuerpo": cuerpo, "autor": request.user, "activa": True},
            )
    respuestas = RespuestaGuardada.objects.all()
    return render(request, "bandeja/respuestas/list.html", {"respuestas": respuestas})


@login_required
def respuestas_buscar(request):
    """Endpoint JSON para autocompletado /slug en el composer."""
    q = (request.GET.get("q") or "").strip()
    qs = RespuestaGuardada.objects.filter(activa=True)
    if q:
        qs = qs.filter(slug__icontains=q) | qs.filter(titulo__icontains=q)
    data = [
        {"slug": r.slug, "titulo": r.titulo, "cuerpo": r.cuerpo}
        for r in qs[:10]
    ]
    return JsonResponse({"items": data})
