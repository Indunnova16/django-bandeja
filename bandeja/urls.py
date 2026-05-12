"""URLs del paquete bandeja.

Incluir desde el huésped con:
    path("bandeja/", include("bandeja.urls"))
"""
from django.urls import path

from bandeja.views import inbox as inbox_views
from bandeja.views.webhook import WebhookView

app_name = "bandeja"

urlpatterns = [
    path("webhook/<slug:channel_slug>/", WebhookView.as_view(), name="webhook"),

    # Inbox UI
    path("inbox/", inbox_views.inbox, name="inbox"),
    path("inbox/c/<int:conversacion_id>/", inbox_views.conversacion_view, name="conversacion"),
    path("inbox/c/<int:conversacion_id>/enviar/", inbox_views.enviar, name="enviar"),
    path("inbox/c/<int:conversacion_id>/estado/", inbox_views.cambiar_estado, name="cambiar_estado"),
    path("inbox/c/<int:conversacion_id>/posponer/", inbox_views.posponer, name="posponer"),
    path("inbox/c/<int:conversacion_id>/etiqueta/", inbox_views.toggle_etiqueta, name="toggle_etiqueta"),
    path("inbox/c/<int:conversacion_id>/macros/<int:macro_id>/aplicar/", inbox_views.aplicar_macro, name="aplicar_macro"),

    # Etiquetas CRUD
    path("etiquetas/", inbox_views.etiquetas_list, name="etiquetas"),
    path("etiquetas/<slug:slug>/toggle/", inbox_views.etiqueta_toggle, name="etiqueta_toggle"),

    # Respuestas guardadas
    path("respuestas/", inbox_views.respuestas_list, name="respuestas"),
    path("respuestas/buscar/", inbox_views.respuestas_buscar, name="respuestas_buscar"),
]
