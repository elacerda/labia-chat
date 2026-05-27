"""Exceções internas de autenticação e autorização."""

from http import HTTPStatus


class AuthenticationError(Exception):
    """Erro de autenticação: token inválido, ausente ou expirado."""

    def __init__(self, message: str = "Invalid or missing authentication token"):
        self.message = message
        self.status_code = HTTPStatus.UNAUTHORIZED
        super().__init__(self.message)




class AuthorizationError(Exception):
    """Erro de autorização: usuário sem role exigida ou inativo."""

    def __init__(
        self,
        message: str = "User does not have required role or is not active",
    ):
        self.message = message
        self.status_code = HTTPStatus.FORBIDDEN
        super().__init__(self.message)


class ExternalServiceError(Exception):
    """Erro de serviço externo: timeout ou falha de rede no ADSS."""

    def __init__(self, message: str = "External service (ADSS) is unavailable"):
        self.message = message
        self.status_code = HTTPStatus.SERVICE_UNAVAILABLE
        super().__init__(self.message)
