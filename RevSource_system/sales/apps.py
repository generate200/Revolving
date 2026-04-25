from django.apps import AppConfig


class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sales'
    verbose_name = 'Sales & POS'
    
    def ready(self):
        """Register signals when app is ready"""
        import sales.signals  # noqa

