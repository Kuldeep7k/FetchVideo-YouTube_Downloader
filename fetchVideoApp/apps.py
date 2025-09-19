from django.apps import AppConfig


class FetchvideoappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fetchVideoApp'

    def ready(self):
        """Import signals when the app is ready"""
        import fetchVideoApp.signals  # noqa
