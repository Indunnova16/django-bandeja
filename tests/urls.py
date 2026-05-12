"""URL config para tests del paquete."""
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from django.urls import include, path

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("bandeja/", include("bandeja.urls")),
]
