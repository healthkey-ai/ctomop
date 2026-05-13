from django.apps import AppConfig


class OmopCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'omop_core'

    def ready(self):
        import omop_core.signals  # noqa: F401 — registers OMOP post_save handlers
