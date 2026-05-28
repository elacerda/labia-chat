"""Testes unitários para as configurações da aplicação."""

import os

import pytest

from labia_chat.core.config import Settings


class TestSettings:
    """Testes para as configurações da aplicação."""

    def test_settings_defaults(self):
        """Verifica que os valores default estão corretos."""
        settings = Settings()

        # Configurações da aplicação
        assert settings.app_name == "labia-chat"
        assert settings.app_env == "development"
        assert settings.app_debug is True

        # Configurações de CORS
        assert settings.cors_allow_origins == "http://localhost:3000,https://ai-scope.cbpf.br"

        # Configurações do ADSS
        assert settings.adss_base_url == "https://ai-scope.cbpf.br/adss/v1"
        assert settings.adss_required_role == "chat_vllm"
        assert settings.adss_auth_cache_ttl_seconds == 300
        assert settings.adss_timeout_seconds == 10

        # Configurações do banco de dados (pode ser setado por variável de ambiente)
        # assert settings.database_url is None  # Ignorado pois DATABASE_URL pode estar definido no ambiente  # noqa: E501

        # Configurações do vLLM
        assert settings.vllm_base_url == "http://127.0.0.1:8000"
        assert settings.vllm_model == "qwen-coder-next"
        assert settings.vllm_timeout_seconds == 30
        assert settings.vllm_api_key is None

    def test_cors_origins_list(self):
        """Verifica que cors_origins_list retorna a lista correta."""
        settings = Settings()
        assert settings.cors_origins_list == [
            "http://localhost:3000",
            "https://ai-scope.cbpf.br",
        ]

    def test_is_production(self):
        """Verifica que is_production funciona corretamente."""
        # Em produção com app_debug=False, is_debug deve ser False
        settings_prod = Settings(app_env="production", app_debug=False)
        assert settings_prod.is_production is True
        assert settings_prod.is_debug is False

        # Em desenvolvimento com app_debug=True, is_debug deve ser True
        settings_dev = Settings(app_env="development", app_debug=True)
        assert settings_dev.is_production is False
        assert settings_dev.is_debug is True

        # Em produção com app_debug=True (caso raro), is_debug deve ser True
        settings_prod_debug = Settings(app_env="production", app_debug=True)
        assert settings_prod_debug.is_production is True
        assert settings_prod_debug.is_debug is True

    def test_is_debug(self):
        """Verifica que is_debug funciona corretamente."""
        settings = Settings(app_debug=True)
        assert settings.is_debug is True

        settings_prod = Settings(app_debug=False, app_env="production")
        assert settings_prod.is_debug is False

    @pytest.mark.parametrize(
        "env_vars,expected",
        [
            (
                {"VLLM_BASE_URL": "http://custom-host:8080"},
                {"vllm_base_url": "http://custom-host:8080"},
            ),
            (
                {"VLLM_MODEL": "llama-3-70b"},
                {"vllm_model": "llama-3-70b"},
            ),
            (
                {"VLLM_TIMEOUT_SECONDS": "60"},
                {"vllm_timeout_seconds": 60},
            ),
            (
                {"VLLM_API_KEY": "my-secret-key"},
                {"vllm_api_key": "my-secret-key"},
            ),
            (
                {"VLLM_API_KEY": ""},
                {"vllm_api_key": ""},
            ),
            (
                {
                    "VLLM_BASE_URL": "http://remote-host:9000",
                    "VLLM_MODEL": "mistral-7b",
                    "VLLM_TIMEOUT_SECONDS": "120",
                },
                {
                    "vllm_base_url": "http://remote-host:9000",
                    "vllm_model": "mistral-7b",
                    "vllm_timeout_seconds": 120,
                },
            ),
        ],
    )
    def test_settings_override_by_environment_variables(
        self, env_vars: dict[str, str], expected: dict[str, str | int]
    ):
        """Verifica que as configurações podem ser sobrescritas por variáveis de ambiente."""  # noqa: E501
        # Salva os valores originais
        original_env = {k: os.environ.get(k) for k in env_vars}

        try:
            # Define as variáveis de ambiente
            for key, value in env_vars.items():
                os.environ[key] = value

            # Cria uma nova instância de Settings
            settings = Settings()

            # Verifica os valores
            for key, expected_value in expected.items():
                assert getattr(settings, key) == expected_value
        finally:
            # Restaura os valores originais
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
