"""Rotas da API do labia-chat."""

from labia_chat.api.routes.auth import router as auth_router  # noqa: F401
from labia_chat.api.routes.chat import router as chat_router  # noqa: F401
from labia_chat.api.routes.health import router as health_router  # noqa: F401
