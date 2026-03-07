from django.apps import AppConfig


class TicketsConfig(AppConfig):
    """Configuration for the tickets app."""
    name = 'tickets'

    def ready(self):
        """Import signals to ensure they are registered when the app is ready."""
        import tickets.signals