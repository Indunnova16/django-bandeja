"""Smoke tests del paquete: importable, AppConfig carga, conf devuelve defaults."""
import bandeja
from bandeja import conf


def test_version():
    assert bandeja.__version__ == "0.0.1"


def test_conf_defaults():
    assert conf.get_channels() == {}
    assert conf.get_sla_primera_respuesta_min() == 15
    assert conf.is_csat_enabled() is False
    assert "LeastBusyStrategy" in conf.get_assignment_strategy_path()


def test_timestampedmodel_abstract():
    from bandeja.models import TimeStampedModel
    assert TimeStampedModel._meta.abstract is True
