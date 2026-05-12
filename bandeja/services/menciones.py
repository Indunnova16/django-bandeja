"""Parser de menciones `@usuario` en notas privadas + notificación opcional."""
from __future__ import annotations

import re

from django.contrib.auth import get_user_model

from bandeja.models import Mencion, Mensaje

_MENCION_RE = re.compile(r"@(\w+)")


def parsear_menciones(mensaje: Mensaje) -> list[Mencion]:
    """Detecta `@username` en mensaje y crea `Mencion` por cada match válido.

    Solo procesa mensajes con `es_nota_privada=True`. Devuelve la lista de
    `Mencion` creadas (puede estar vacía).
    """
    if not mensaje.es_nota_privada:
        return []
    usernames = set(_MENCION_RE.findall(mensaje.contenido or ""))
    if not usernames:
        return []

    User = get_user_model()
    users = User.objects.filter(username__in=usernames, is_active=True)
    creadas: list[Mencion] = []
    for u in users:
        mencion, created = Mencion.objects.get_or_create(
            mensaje=mensaje, mencionado=u,
        )
        if created:
            creadas.append(mencion)
    return creadas
