"""Fusión de contactos duplicados.

Reasigna todos los Mensajes, Conversaciones, ConversacionEtiqueta,
ContactoEtiqueta del contacto `origen` al `destino`, marca el origen como
fusionado y registra en BitacoraContacto.
"""
from __future__ import annotations

from django.db import transaction

from bandeja.models import (
    BitacoraContacto,
    ContactoEtiqueta,
    Conversacion,
    Mensaje,
)


@transaction.atomic
def merge_contactos(origen, destino, autor=None) -> dict:
    """Fusiona `origen` en `destino`. Devuelve resumen `{mensajes, conversaciones, etiquetas}`.

    Reglas:
    - Mensajes y Conversaciones del origen pasan al destino.
    - Etiquetas del origen se agregan al destino (UNIQUE evita dups).
    - Origen queda con `fusionado_en=destino` y se conservan sus campos.
    - Bitácora registra la operación en ambos contactos.
    """
    if origen.pk == destino.pk:
        raise ValueError("origen y destino son el mismo contacto")
    if origen.fusionado_en_id:
        raise ValueError(f"Contacto #{origen.pk} ya fue fusionado")

    n_mensajes = Mensaje.objects.filter(contacto=origen).update(contacto=destino)
    n_convs = Conversacion.objects.filter(contacto=origen).update(contacto=destino)

    etiquetas_origen = list(
        ContactoEtiqueta.objects.filter(contacto=origen).values_list("etiqueta_id", flat=True)
    )
    n_etiquetas = 0
    for etq_id in etiquetas_origen:
        _, created = ContactoEtiqueta.objects.get_or_create(
            contacto=destino, etiqueta_id=etq_id, defaults={"created_by": autor},
        )
        if created:
            n_etiquetas += 1
    ContactoEtiqueta.objects.filter(contacto=origen).delete()

    # Tomar fecha mínima/máxima entre ambos contactos
    if origen.fecha_primer_mensaje:
        if not destino.fecha_primer_mensaje or origen.fecha_primer_mensaje < destino.fecha_primer_mensaje:
            destino.fecha_primer_mensaje = origen.fecha_primer_mensaje
    if origen.fecha_ultimo_mensaje:
        if not destino.fecha_ultimo_mensaje or origen.fecha_ultimo_mensaje > destino.fecha_ultimo_mensaje:
            destino.fecha_ultimo_mensaje = origen.fecha_ultimo_mensaje
    destino.save()

    origen.fusionado_en = destino
    origen.save(update_fields=["fusionado_en", "updated_at"])

    resumen = {
        "mensajes": n_mensajes,
        "conversaciones": n_convs,
        "etiquetas_nuevas": n_etiquetas,
    }
    BitacoraContacto.objects.create(
        contacto=destino, accion="merge_target",
        detalle={"origen_id": origen.pk, **resumen}, autor=autor,
    )
    BitacoraContacto.objects.create(
        contacto=origen, accion="merge_source",
        detalle={"destino_id": destino.pk, **resumen}, autor=autor,
    )
    return resumen
