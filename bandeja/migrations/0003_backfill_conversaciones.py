"""Backfill: agrupa Mensajes existentes en Conversaciones por ventana 24h."""
from datetime import timedelta

from django.db import migrations


VENTANA = timedelta(hours=24)


def backfill_conversaciones(apps, schema_editor):
    Contacto = apps.get_model("bandeja", "Contacto")
    Conversacion = apps.get_model("bandeja", "Conversacion")
    Mensaje = apps.get_model("bandeja", "Mensaje")
    Canal = apps.get_model("bandeja", "Canal")

    # Si no hay mensajes, no hay nada que hacer.
    if not Mensaje.objects.exists():
        return

    canal_default = Canal.objects.first()

    for contacto in Contacto.objects.all():
        mensajes = list(
            Mensaje.objects.filter(contacto=contacto, conversacion__isnull=True)
            .order_by("timestamp")
        )
        if not mensajes:
            continue

        conv = None
        last_ts = None
        for msg in mensajes:
            if conv is None or (last_ts and msg.timestamp - last_ts > VENTANA):
                # Cerrar la anterior si existe
                if conv is not None:
                    conv.estado = "resuelta"
                    conv.fecha_resolucion = last_ts
                    conv.fecha_ultimo_mensaje = last_ts
                    conv.save()
                conv = Conversacion.objects.create(
                    contacto=contacto,
                    canal=msg.canal or canal_default,
                    estado="abierta",
                    fecha_apertura=msg.timestamp,
                    fecha_ultimo_mensaje=msg.timestamp,
                )
            msg.conversacion = conv
            msg.save(update_fields=["conversacion"])
            last_ts = msg.timestamp

        if conv is not None:
            conv.fecha_ultimo_mensaje = last_ts
            # Conversación más reciente sin actividad >24h queda "pendiente"
            conv.save()


def reverse_noop(apps, schema_editor):
    """No-op: borrar conversaciones generadas requeriría marca; skip."""


class Migration(migrations.Migration):
    dependencies = [
        ("bandeja", "0002_conversacionetiqueta_etiqueta_respuestaguardada_and_more"),
    ]
    operations = [
        migrations.RunPython(backfill_conversaciones, reverse_noop),
    ]
