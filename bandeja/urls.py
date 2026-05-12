"""URLs del paquete bandeja.

Incluir desde el huésped con:
    path("bandeja/", include("bandeja.urls"))
"""
from django.urls import path

from bandeja.views.webhook import WebhookView

app_name = "bandeja"

urlpatterns = [
    path("webhook/<slug:channel_slug>/", WebhookView.as_view(), name="webhook"),
]
