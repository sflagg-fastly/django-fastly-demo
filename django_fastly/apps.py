from django.apps import AppConfig


class FastlyAppConfig(AppConfig):
    name = "django_fastly"
    verbose_name = "Fastly"

    def ready(self):
        from . import signals  # noqa
