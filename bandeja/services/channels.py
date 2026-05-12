"""Lookup de adapter por slug de canal."""
from __future__ import annotations

from functools import lru_cache

from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from bandeja import conf
from bandeja.channels.base import ChannelAdapter


@lru_cache(maxsize=None)
def get_adapter(slug: str) -> ChannelAdapter:
    """Devuelve el adapter configurado para el canal `slug`.

    Lookup en `settings.BANDEJA_CHANNELS[slug]`. La clase del adapter se
    importa por dotted path en `adapter`. Resultado cacheado por proceso.
    """
    channels = conf.get_channels()
    if slug not in channels:
        raise ImproperlyConfigured(
            f"Canal '{slug}' no está configurado en BANDEJA_CHANNELS. "
            f"Disponibles: {sorted(channels.keys())}"
        )
    config = dict(channels[slug])
    adapter_path = config.pop("adapter", "")
    if not adapter_path:
        raise ImproperlyConfigured(f"Canal '{slug}' sin 'adapter' configurado.")
    adapter_cls = import_string(adapter_path)
    return adapter_cls(slug=slug, config=config)
