"""Tests de RoundRobinByShift: reparto justo entre agentes en turno."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from bandeja.assignment.round_robin import RoundRobinByShift
from bandeja.models import BandejaAgentProfile


@pytest.fixture
def tres_agentes():
    User = get_user_model()
    users = []
    for username in ("ana", "bea", "carla"):
        u = User.objects.create_user(username=username, is_active=True)
        BandejaAgentProfile.objects.create(user=u, activo=True)
        users.append(u)
    return users


@pytest.mark.django_db
def test_round_robin_reparto_justo(tres_agentes, settings):
    """10 asignaciones con 3 agentes en turno → reparto 4-3-3 (orden de llegada)."""
    settings.BANDEJA_SHIFT_RESOLVER = "tests.test_round_robin.resolver_todos"

    strat = RoundRobinByShift()
    asignados = []
    for _ in range(10):
        u = strat.assign()
        asignados.append(u.username)

    from collections import Counter
    cnt = Counter(asignados)
    # 10 / 3 = 4 + 3 + 3
    assert sorted(cnt.values()) == [3, 3, 4]


@pytest.mark.django_db
def test_round_robin_sin_turno_cae_a_least_busy(tres_agentes, settings):
    """Si SHIFT_RESOLVER no devuelve a nadie, se cae al fallback LeastBusy."""
    settings.BANDEJA_SHIFT_RESOLVER = "tests.test_round_robin.resolver_vacio"

    strat = RoundRobinByShift()
    u = strat.assign()
    assert u is not None  # least_busy devuelve alguno


@pytest.mark.django_db
def test_round_robin_filtra_inactivos(tres_agentes, settings):
    """Si un agente del resolver tiene bandeja_profile.activo=False, se ignora."""
    settings.BANDEJA_SHIFT_RESOLVER = "tests.test_round_robin.resolver_todos"
    inactiva = tres_agentes[0]
    inactiva.bandeja_profile.activo = False
    inactiva.bandeja_profile.save()

    strat = RoundRobinByShift()
    asignados = [strat.assign().username for _ in range(6)]
    assert "ana" not in asignados
    assert set(asignados) == {"bea", "carla"}


# Resolvers usados por los tests (importables por dotted path)
def resolver_todos():
    from django.contrib.auth import get_user_model
    return get_user_model().objects.all()


def resolver_vacio():
    from django.contrib.auth import get_user_model
    return get_user_model().objects.none()
