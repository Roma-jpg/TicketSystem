# TicketSystem141/asgi.py
import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

from apps.tickets.routing import websocket_urlpatterns as ticket_ws
from apps.notifications.routing import websocket_urlpatterns as notification_ws

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TicketSystem141.settings")
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(ticket_ws + notification_ws)
        )
    ),
})