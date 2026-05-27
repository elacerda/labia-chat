"""Endpoint de health check da API."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Verifica se o backend está operacional.

    Retorna:
        dict com status "ok" e nome do serviço.
    """
    return {"status": "ok", "service": "labia-chat"}
