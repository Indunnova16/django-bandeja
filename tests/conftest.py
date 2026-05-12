"""Pytest fixtures globales."""
import django


def pytest_configure():
    django.setup()
