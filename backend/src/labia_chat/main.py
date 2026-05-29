"""App FastAPI principal do labia-chat."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from labia_chat.api.routes import auth_router, chat_router, health_router
from labia_chat.core.config import settings
from labia_chat.db.session import dispose_engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Gerenciar ciclo de vida da aplicação FastAPI."""
    yield
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    debug=settings.is_debug,
    lifespan=lifespan,
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(health_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.is_debug)
