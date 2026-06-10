from __future__ import annotations

from asgiref.wsgi import WsgiToAsgi

from .app import app

asgi_app = WsgiToAsgi(app)
