"""Señales que dispara el paquete bandeja.

Las apps huéspedes se enganchan a estas señales para integrar su dominio
de negocio (crear `Oportunidad`, enviar CSAT, etc.) sin modificar el
paquete.

Convención: el sender es siempre la CLASE del modelo principal del evento
(Conversacion, Mensaje, …) para permitir filtros `sender=...` en `connect`.
"""
from django.dispatch import Signal

mensaje_recibido = Signal()
"""Disparado al persistir un mensaje entrante. kwargs: mensaje, contacto, canal."""

mensaje_enviado = Signal()
"""Disparado al enviar (saliente). kwargs: mensaje, contacto, canal, usuario."""

conversacion_creada = Signal()
"""Disparado al crear una nueva Conversacion (Fase 3). kwargs: conversacion."""

conversacion_resuelta = Signal()
"""Conversación cerrada por un agente. kwargs: conversacion, resuelta_por."""

agente_asignado = Signal()
"""Cambio de asignación de agente. kwargs: conversacion, agente_anterior, agente_nuevo."""

sla_vencido = Signal()
"""SLA de primera respuesta excedido. kwargs: conversacion, minutos_excedidos."""
