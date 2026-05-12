# indunnova-bandeja

Librería Django reusable para bandeja omnichannel (WhatsApp / IG / FB / email),
con pipeline de asignación, etiquetas, macros, SLA y snooze.

Diseñada para los aplicativos Indunnova (LaCintería, ObrajeCRM, Carnes del
Sebastián, …). Stack: Django 5.1+, Python 3.12+, HTMX/Alpine/Tailwind.

## Estado

`v0.0.x` — scaffold inicial. El diseño completo vive en el repo piloto
[LaCinteriaComercial](https://github.com/Indunnova16/LaCinteriaComercial):

- `BANDEJA_PACKAGE_DESIGN.md` — arquitectura, patrones de extensión.
- `ROADMAP_CHATWOOT.md` — 12 features inspiradas en Chatwoot.

## Instalación

```bash
pip install git+https://github.com/Indunnova16/django-bandeja@v0.0.1
```

## Configuración mínima

```python
# settings.py
INSTALLED_APPS = [..., "bandeja"]

BANDEJA_CHANNELS = {
    "principal": {
        "adapter": "bandeja.channels.whatsapp_cloud.WhatsAppCloudAdapter",
        "phone_number_id": env("WA_PHONE_ID"),
        "verify_token": env("WA_VERIFY_TOKEN"),
        "app_secret": env("META_APP_SECRET"),
        "access_token": env("WA_TOKEN"),
    },
}

BANDEJA_ASSIGNMENT_STRATEGY = "bandeja.assignment.least_busy.LeastBusyStrategy"
BANDEJA_SLA_PRIMERA_RESPUESTA_MIN = 15
```

```python
# urls.py
path("bandeja/", include("bandeja.urls")),
```

```bash
python manage.py migrate bandeja
```

## Tests

```bash
pip install -e .[dev]
pytest
```
