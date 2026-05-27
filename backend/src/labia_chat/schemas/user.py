"""Schemas Pydantic para usuário e roles do ADSS."""

from pydantic import BaseModel


class ADSSRole(BaseModel):
    """Modelo de role do ADSS."""

    id: int
    name: str
    description: str | None = None


class ADSSUser(BaseModel):
    """Modelo de usuário retornado pelo ADSS /users/me."""

    id: str
    username: str
    email: str
    full_name: str
    is_active: bool
    is_staff: bool
    is_superuser: bool
    roles: list[ADSSRole]


class AuthenticatedUser(BaseModel):
    """Modelo normalizado de usuário autenticado para uso interno."""

    id: str
    username: str
    email: str
    full_name: str
    is_active: bool
    is_staff: bool
    is_superuser: bool
    roles: list[str]
