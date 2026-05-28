"""Configurações da aplicação usando Pydantic Settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Caminho absoluto para o arquivo .env (um diretório acima do backend/)
BACKEND_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Configurações da aplicação labia-chat."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Configurações da aplicação
    app_name: str = "labia-chat"
    app_env: str = "development"
    app_debug: bool = True

    # Configurações de CORS
    cors_allow_origins: str = "http://localhost:3000,https://ai-scope.cbpf.br"

    # Configurações do ADSS (AI-Scope)
    adss_base_url: str = "https://ai-scope.cbpf.br/adss/v1"
    adss_required_role: str = "chat_vllm"
    adss_auth_cache_ttl_seconds: int = 300
    adss_timeout_seconds: int = 10

    # Configurações do banco de dados (MVP 2)
    database_url: str | None = None

    # Configurações do vLLM (MVP 4)
    vllm_base_url: str = "http://127.0.0.1:8000"
    vllm_model: str = "qwen-coder-next"
    vllm_timeout_seconds: int = 30

    @property
    def cors_origins_list(self) -> list[str]:
        """Retorna a lista de origins permitidos a partir da string de configuração."""
        origins = self.cors_allow_origins.split(",")
        return [origin.strip() for origin in origins if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Verifica se o ambiente é produção."""
        return self.app_env == "production"

    @property
    def is_debug(self) -> bool:
        """Verifica se o modo debug está ativo."""
        return self.app_debug or not self.is_production


settings = Settings()
