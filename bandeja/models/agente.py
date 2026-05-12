from django.conf import settings
from django.db import models

from bandeja.models import TimeStampedModel


class BandejaAgentProfile(TimeStampedModel):
    """Perfil de un usuario en cuanto a su rol en la bandeja.

    El "agente" es siempre un `settings.AUTH_USER_MODEL`. Este perfil
    captura los datos específicos de bandeja (turno, número saliente,
    estado de cola) sin tocar el modelo de usuario.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bandeja_profile",
    )
    nombre_display = models.CharField(
        max_length=120,
        blank=True,
        help_text="Sobrescribe `user.get_full_name()` en la UI de bandeja.",
    )
    wa_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Número del agente para handover / coordinación interna.",
    )
    horario_inicio = models.TimeField(null=True, blank=True)
    horario_fin = models.TimeField(null=True, blank=True)
    activo = models.BooleanField(
        default=True,
        help_text="Si False, el agente no recibe asignaciones automáticas.",
    )
    ultima_asignacion_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Para round-robin justo: el agente con valor más antiguo recibe la siguiente conversación.",
    )

    class Meta:
        app_label = "bandeja"
        ordering = ["user__username"]

    def __str__(self):
        return self.nombre_display or self.user.get_full_name() or self.user.username

    @property
    def nombre(self) -> str:
        """Display name resuelto: profile override → user full name → username."""
        return self.nombre_display or self.user.get_full_name() or self.user.username
