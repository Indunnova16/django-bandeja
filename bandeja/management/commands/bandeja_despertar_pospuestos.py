"""Comando idempotente: despierta conversaciones pospuestas cuyo plazo venció.

Programar en Cloud Scheduler cada 15 min apuntando a un endpoint que
invoque este comando, o ejecutar como `python manage.py bandeja_despertar_pospuestos`.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from bandeja.models import Conversacion


class Command(BaseCommand):
    help = "Pasa a 'abierta' las Conversaciones pospuestas cuyo pospuesta_hasta ya venció."

    def handle(self, *args, **options):
        ahora = timezone.now()
        qs = Conversacion.objects.filter(
            estado="pospuesta", pospuesta_hasta__lte=ahora,
        )
        n = qs.update(estado="abierta", pospuesta_hasta=None, updated_at=ahora)
        self.stdout.write(self.style.SUCCESS(f"Despertadas {n} conversaciones."))
