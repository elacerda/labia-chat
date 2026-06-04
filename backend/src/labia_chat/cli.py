"""Entrypoint CLI do labia-chat."""

import argparse
import getpass
import os
from importlib import metadata

from labia_chat import __version__
from labia_chat.cli_auth import LoginError, prompt_for_ai_scope_login
from labia_chat.cli_client import (
    AuthError,
    BackendError,
    CLIClient,
    ConnectionError,
    NotFoundError,
    ValidationError,
)
from labia_chat.cli_client import (
    PermissionError as CLIPermissionError,
)
from labia_chat.cli_config import (
    resolve_api_url_with_source as resolve_api_url_with_source_config,
)
from labia_chat.cli_config import (
    resolve_show_last_default_with_source as _resolve_show_last,
)
from labia_chat.cli_config import (
    resolve_streaming_default_with_source as _resolve_streaming,
)
from labia_chat.cli_config import (
    resolve_token_optional_with_source as resolve_token_optional_with_source_config,
)
from labia_chat.cli_ui import (
    print_assistant_message,
    print_banner,
    print_error,
    print_history_header,
    print_info,
    print_new_conversation_success,
    print_streaming_start,
    print_user_label,
    print_user_message,
)
from labia_chat.cli_ui import (
    print_help as print_help_ui,
)

DEFAULT_API_URL = "http://127.0.0.1:8010"
DEFAULT_CHAT_TITLE = "CLI chat"
DOCTOR_HINT = "Sugestão: execute `labia-chat doctor` para diagnosticar o ambiente."
CLI_HANDLED_ERRORS = (
    AuthError,
    CLIPermissionError,
    NotFoundError,
    ValidationError,
    BackendError,
    ConnectionError,
)
HELP_EXAMPLES = """Exemplos:
  labia-chat
  labia-chat --last
  labia-chat config init
  labia-chat doctor
"""


def get_cli_version() -> str:
    """
    Retorna a versão instalada do pacote.

    Returns:
        Versão do pacote ou fallback local.
    """
    try:
        return metadata.version("labia-chat")
    except metadata.PackageNotFoundError:
        return __version__


def resolve_api_url(args_api_url: str | None) -> str:
    """
    Resolve a URL da API na ordem: flag > env > default.

    Args:
        args_api_url: Valor passado via --api-url.

    Returns:
        A URL da API resolvida.
    """
    if args_api_url:
        return args_api_url
    env_url = os.environ.get("LABIA_CHAT_API_URL")
    if env_url:
        return env_url
    return DEFAULT_API_URL


def resolve_api_url_with_source(args_api_url: str | None) -> tuple[str, str]:
    """
    Resolve a URL da API com a origem detectável.

    Args:
        args_api_url: Valor passado via --api-url.

    Returns:
        Tupla com URL resolvida e origem: argument, env ou default.
    """
    if args_api_url:
        return args_api_url, "argument"
    env_url = os.environ.get("LABIA_CHAT_API_URL")
    if env_url:
        return env_url, "env"
    return DEFAULT_API_URL, "default"


def resolve_token(args_token: str | None) -> str:
    """
    Resolve o token na ordem: flag > env > prompt.

    Args:
        args_token: Valor passado via --token.

    Returns:
        O token resolvido.
    """
    if args_token:
        return args_token
    env_token = os.environ.get("LABIA_CHAT_TOKEN")
    if env_token:
        return env_token
    return getpass.getpass("AI-Scope token: ")


def resolve_token_optional_with_source(
    args_token: str | None,
) -> tuple[str | None, str]:
    """
    Resolve o token sem prompt interativo e com origem detectável.

    Args:
        args_token: Valor passado via --token.

    Returns:
        Tupla com token opcional e origem: argument, env ou missing.
    """
    if args_token:
        return args_token, "argument"
    env_token = os.environ.get("LABIA_CHAT_TOKEN")
    if env_token:
        return env_token, "env"
    return None, "missing"


def resolve_token_required(args_token: str | None) -> str | None:
    """
    Resolve token para comandos não interativos sem prompt.

    Returns:
        Token resolvido, ou None quando ausente.
    """
    token, _source = resolve_token_optional_with_source_config(args_token)
    return token


def resolve_interactive_chat_token(args_token: str | None) -> str:
    """
    Resolve token para chat interativo, fazendo login AI-Scope se necessário.

    O token obtido por login permanece apenas em memória no processo atual.
    """
    token, _source = resolve_token_optional_with_source_config(args_token)
    if token:
        return token
    return prompt_for_ai_scope_login()


def print_missing_token_error() -> None:
    """Imprime erro estável para comandos sem token e sem login interativo."""
    print(
        "Erro: token AI-Scope ausente. Informe --token ou LABIA_CHAT_TOKEN. "
        "Login automático só é usado no chat interativo."
    )


def print_cli_error(error: Exception, context: str | None = None) -> None:
    """
    Imprime erro com orientação de diagnóstico.

    Args:
        error: Exceção tratada pelo CLI.
        context: Contexto opcional para a mensagem.
    """
    if context:
        print(f"Erro {context}: {error}")
    else:
        print(f"Erro: {error}")
    if "labia-chat doctor" not in str(error):
        print(DOCTOR_HINT)


def print_diagnostic(status: str, label: str, detail: str = "") -> None:
    """
    Imprime uma linha estável de diagnóstico.

    Args:
        status: Status curto, como ok, fail ou skip.
        label: Nome da checagem.
        detail: Detalhe opcional.
    """
    line = f"[{status}] {label}"
    if detail:
        line = f"{line}: {detail}"
    print(line)


def print_help() -> None:
    """Imprime a ajuda dos comandos disponíveis."""
    print_help_ui()


def print_messages(messages: list[dict], show_last: int) -> None:
    """
    Imprime as últimas N mensagens.

    Args:
        messages: Lista de mensagens.
        show_last: Número de mensagens a exibir.
    """
    if not messages:
        print_info("Nenhuma mensagem ainda.")
        return

    # Pega as últimas N mensagens
    last_messages = messages[-show_last:]

    for msg in last_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        # Formata a role para exibição
        if role == "user":
            print_user_message(content)
        elif role == "assistant":
            print_assistant_message(content)
        else:
            print(f"[{role}]: {content}")
        print()


def print_user_summary(user_data: dict) -> None:
    """
    Imprime um resumo compacto do usuário.

    Args:
        user_data: Dados do usuário retornado por /auth/me.
    """
    username = user_data.get("username", "desconhecido")
    email = user_data.get("email", "")
    is_active = user_data.get("is_active", False)
    user_id = user_data.get("id", "")

    print(f"Usuário: {username}")
    if email:
        print(f"E-mail: {email}")
    if user_id:
        print(f"ID: {user_id}")
    status = "Sim" if is_active else "Não"
    print(f"Ativo: {status}")


def print_conversation_summary(conversation: dict) -> None:
    """
    Imprime um resumo compacto da conversa.

    Args:
        conversation: Dados da conversa criada.
    """
    conv_id = conversation.get("id", "desconhecido")
    title = conversation.get("title")

    print(f"Conversa criada: {conv_id}")
    if title:
        print(f"Título: {title}")


def print_assistant_response(response: dict) -> None:
    """
    Imprime apenas a resposta do assistente.

    Args:
        response: Dados da resposta do assistente.
    """
    content = response.get("content", "")
    print(content)


def chat_stream_enabled(args: argparse.Namespace) -> bool:
    return getattr(args, "stream", True)


def chat_title(args: argparse.Namespace) -> str:
    return getattr(args, "title", None) or DEFAULT_CHAT_TITLE


def get_most_recent_conversation(client: CLIClient) -> str | None:
    """Return the user's most recent conversation ID.

    Parameters
    ----------
    client
        Authenticated CLI client.

    Returns
    -------
    str | None
        Most recent conversation ID, or None if no conversations exist.
    """
    conversations = client.list_conversations(limit=1, offset=0)
    if not conversations:
        return None

    conversation_id = conversations[0].get("id")
    if not isinstance(conversation_id, str) or not conversation_id:
        return None

    return conversation_id


def validate_resume_last_args(args: argparse.Namespace) -> tuple[bool, str]:
    """
    Valida argumentos de resume-last.

    Args:
        args: Argumentos da linha de comando.

    Returns:
        Tupla (is_valid, error_message).
    """
    if getattr(args, "last", False) or getattr(args, "resume_last", False):
        if getattr(args, "conversation_id", None):
            return False, (
                "Erro: --conversation-id não pode ser usado com --last/--resume-last. "
                "Use apenas um ou outro."
            )
    return True, ""


def print_chat_banner(
    api_url: str,
    username: str | None,
    conversation_id: str,
    stream: bool,
) -> None:
    print_banner(api_url, username, conversation_id, stream)


def create_chat_conversation(
    client: CLIClient,
    title: str,
) -> str:
    conversation = client.create_conversation(title=title)
    conversation_id = conversation.get("id", "desconhecido")
    client.conversation_id = conversation_id
    return conversation_id


def print_chat_history(client: CLIClient, limit: int) -> None:
    if not client.conversation_id:
        print_error("Nenhuma conversa selecionada.")
        return
    if limit <= 0:
        print_info("Histórico desativado por --show-last 0.")
        return

    messages = client.list_messages(client.conversation_id, limit=limit)
    if not messages:
        print_info("Nenhuma mensagem ainda.")
        return

    print_history_header(min(limit, len(messages)))
    print_messages(messages, limit)


def config_show_command(args: argparse.Namespace) -> int:
    """
    Exibe a configuração resolvida do CLI.

    Args:
        args: Argumentos da linha de comando.

    Returns:
        Código de saída.
    """
    # Resolve API URL com origem (CLI args > env > config > default)
    api_url, api_source = resolve_api_url_with_source_config(args.api_url)

    # Resolve streaming default com origem
    streaming_default, streaming_source = _resolve_streaming(None)

    # Resolve show_last default com origem
    show_last_default, show_last_source = _resolve_show_last(None)

    # Resolve token com origem (nunca do config por segurança)
    token, token_source = resolve_token_optional_with_source_config(args.token)
    token_status = "configurado" if token else "ausente"

    print("Configuração do CLI")
    print(f"URL da API: {api_url}")
    print(f"Origem da URL da API: {api_source}")
    print(f"Streaming padrão: {'habilitado' if streaming_default else 'desabilitado'}")
    print(f"Origem do streaming padrão: {streaming_source}")
    print(f"Mensagens recentes padrão: {show_last_default}")
    print(f"Origem das mensagens recentes padrão: {show_last_source}")
    token_source_display = "ausente" if token_source == "missing" else token_source
    print(f"Status do token: {token_status}")
    print(f"Origem do token: {token_source_display}")
    return 0


def config_init_command(args: argparse.Namespace) -> int:
    """
    Inicializa ou atualiza a configuração local.

    Args:
        args: Argumentos da linha de comando.

    Returns:
        Código de saída.
    """
    from labia_chat.cli_config import get_config_path, save_config

    # Converte valores de string para tipos apropriados
    # argparse usa type=str para --streaming-default, então precisamos converter
    streaming_default = args.streaming_default
    if isinstance(streaming_default, str):
        streaming_default = streaming_default.lower() == "true"

    show_last_default = args.show_last_default
    if isinstance(show_last_default, str):
        # Tenta converter para int, se falhar, usa None
        try:
            show_last_default = int(show_last_default)
        except ValueError:
            show_last_default = None

    # Salva apenas os valores fornecidos (não salva token por segurança)
    save_config(
        api_url=args.api_url,
        streaming_default=streaming_default,
        show_last_default=show_last_default,
    )

    print("Configuração salva com sucesso.")
    print(f"Arquivo: {get_config_path()}")
    return 0


def doctor_command(args: argparse.Namespace) -> int:
    """
    Executa diagnósticos amigáveis do CLI e backend.

    Args:
        args: Argumentos da linha de comando.

    Returns:
        Código de saída.
    """
    api_url, api_source = resolve_api_url_with_source_config(args.api_url)
    token, token_source = resolve_token_optional_with_source_config(args.token)
    has_failure = False

    print("labia-chat doctor")
    print(f"API URL: {api_url} (source: {api_source})")

    if token:
        print(f"Token: configured (source: {token_source})")
    else:
        print("Token: missing")

    client = CLIClient(api_url)

    try:
        try:
            health = client.health_check()
            status = health.get("status", "unknown")
            if status == "ok":
                print_diagnostic("ok", "GET /health", "backend is healthy")
            else:
                print_diagnostic("fail", "GET /health", f"unexpected status {status}")
                has_failure = True
        except (BackendError, ConnectionError) as e:
            print_diagnostic("fail", "GET /health", str(e))
            has_failure = True

        if token:
            client.set_token(token)
            try:
                user_data = client.validate_token()
                username = user_data.get("username", "authenticated user")
                print_diagnostic("ok", "GET /auth/me", str(username))
            except (
                AuthError,
                CLIPermissionError,
                ValidationError,
                BackendError,
                ConnectionError,
            ) as e:
                print_diagnostic("fail", "GET /auth/me", str(e))
                has_failure = True
        else:
            print_diagnostic("skip", "GET /auth/me", "token missing")

        if getattr(args, "with_model", False):
            if not token:
                print_diagnostic("skip", "POST /chat/model/ping", "token missing")
            else:
                try:
                    client.model_ping()
                    print_diagnostic("ok", "POST /chat/model/ping", "model responded")
                except (
                    AuthError,
                    CLIPermissionError,
                    ValidationError,
                    BackendError,
                    ConnectionError,
                ) as e:
                    print_diagnostic("fail", "POST /chat/model/ping", str(e))
                    has_failure = True
    finally:
        client.close()

    return 1 if has_failure else 0


def print_stream_chunks(chunks) -> None:
    """Imprime chunks de streaming sem buffering de linha."""
    for chunk in chunks:
        print(chunk, end="", flush=True)
    print()


def format_datetime(dt_str: str) -> str:
    """
    Formata uma string de datetime ISO para exibição em PT-BR.

    Args:
        dt_str: String de datetime no formato ISO (ex: "2024-01-01T10:00:00Z").

    Returns:
        String formatada (ex: "01/01/2024 10:00").
    """
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return dt_str


def print_conversations_list(conversations: list[dict]) -> None:
    """
    Imprime lista de conversas em formato compacto.

    Args:
        conversations: Lista de conversas.
    """
    if not conversations:
        print("Nenhuma conversa encontrada.")
        return

    print(f"Total de conversas: {len(conversations)}")
    print()

    for conv in conversations:
        conv_id = conv.get("id", "desconhecido")
        title = conv.get("title")
        created_at = conv.get("created_at", "")

        formatted_date = format_datetime(created_at) if created_at else ""

        print(f"[{formatted_date}] {conv_id}")
        if title:
            print(f"  Título: {title}")
        print()


def print_messages_list(messages: list[dict]) -> None:
    """
    Imprime lista de mensagens em formato compacto.

    Args:
        messages: Lista de mensagens.
    """
    if not messages:
        print("Nenhuma mensagem ainda.")
        return

    print(f"Total de mensagens: {len(messages)}")
    print()

    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        created_at = msg.get("created_at", "")

        formatted_date = format_datetime(created_at) if created_at else ""

        if role == "user":
            role_display = "Você"
        elif role == "assistant":
            role_display = "Assistente"
        else:
            role_display = role

        print(f"[{formatted_date}] {role_display}: {content}")
        print()


def auth_me_command(args: argparse.Namespace) -> int:
    """
    Executa o comando 'auth me' para validar token.

    Args:
        args: Argumentos da linha de comando.

    Returns:
        Código de saída (0 para sucesso, 1 para erro).
    """
    api_url = resolve_api_url(args.api_url)
    token = resolve_token_required(args.token)
    if not token:
        print_missing_token_error()
        return 1

    client = CLIClient(api_url)

    try:
        client.set_token(token)
        user_data = client.validate_token()
        print_user_summary(user_data)
        return 0
    except AuthError as e:
        print_cli_error(e)
        return 1
    except CLIPermissionError as e:
        print_cli_error(e)
        return 1
    except ValidationError as e:
        print_cli_error(e)
        return 1
    except BackendError as e:
        print_cli_error(e)
        return 1
    except ConnectionError as e:
        print_cli_error(e)
        return 1
    finally:
        client.close()


def conversations_create_command(args: argparse.Namespace) -> int:
    """
    Executa o comando 'conversations create' para criar nova conversa.

    Args:
        args: Argumentos da linha de comando.

    Returns:
        Código de saída (0 para sucesso, 1 para erro).
    """
    api_url = resolve_api_url(args.api_url)
    token = resolve_token_required(args.token)
    if not token:
        print_missing_token_error()
        return 1

    client = CLIClient(api_url)

    try:
        client.set_token(token)
        title = args.title if args.title else None
        conversation = client.create_conversation(title=title)
        print_conversation_summary(conversation)
        return 0
    except AuthError as e:
        print_cli_error(e)
        return 1
    except CLIPermissionError as e:
        print_cli_error(e)
        return 1
    except ValidationError as e:
        print_cli_error(e)
        return 1
    except BackendError as e:
        print_cli_error(e)
        return 1
    except ConnectionError as e:
        print_cli_error(e)
        return 1
    finally:
        client.close()


def conversations_list_command(args: argparse.Namespace) -> int:
    """
    Executa o comando 'conversations list' para listar conversas.

    Args:
        args: Argumentos da linha de comando.

    Returns:
        Código de saída (0 para sucesso, 1 para erro).
    """
    api_url = resolve_api_url(args.api_url)
    token = resolve_token_required(args.token)
    if not token:
        print_missing_token_error()
        return 1

    client = CLIClient(api_url)

    try:
        client.set_token(token)
        conversations = client.list_conversations(limit=args.limit, offset=args.offset)
        print_conversations_list(conversations)
        return 0
    except AuthError as e:
        print_cli_error(e)
        return 1
    except CLIPermissionError as e:
        print_cli_error(e)
        return 1
    except ValidationError as e:
        print_cli_error(e)
        return 1
    except BackendError as e:
        print_cli_error(e)
        return 1
    except ConnectionError as e:
        print_cli_error(e)
        return 1
    finally:
        client.close()


def messages_list_command(args: argparse.Namespace) -> int:
    """
    Executa o comando 'messages list' para listar mensagens de uma conversa.

    Args:
        args: Argumentos da linha de comando.

    Returns:
        Código de saída (0 para sucesso, 1 para erro).
    """
    api_url = resolve_api_url(args.api_url)
    token = resolve_token_required(args.token)
    if not token:
        print_missing_token_error()
        return 1

    client = CLIClient(api_url)

    try:
        client.set_token(token)
        messages = client.list_messages(
            args.conversation_id, limit=args.limit, offset=args.offset
        )
        print_messages_list(messages)
        return 0
    except AuthError as e:
        print_cli_error(e)
        return 1
    except CLIPermissionError as e:
        print_cli_error(e)
        return 1
    except NotFoundError as e:
        print_cli_error(e)
        return 1
    except ValidationError as e:
        print_cli_error(e)
        return 1
    except BackendError as e:
        print_cli_error(e)
        return 1
    except ConnectionError as e:
        print_cli_error(e)
        return 1
    finally:
        client.close()


def chat_send_command(args: argparse.Namespace) -> int:
    """
    Executa o comando 'chat send' para enviar mensagem não interativa.

    Args:
        args: Argumentos da linha de comando.

    Returns:
        Código de saída (0 para sucesso, 1 para erro).
    """
    api_url = resolve_api_url(args.api_url)
    token = resolve_token_required(args.token)
    if not token:
        print_missing_token_error()
        return 1

    client = CLIClient(api_url)

    try:
        client.set_token(token)
        client.conversation_id = args.conversation_id

        # Valida o token primeiro
        try:
            client.validate_token()
        except AuthError as e:
            print_cli_error(e)
            return 1
        except CLIPermissionError as e:
            print_cli_error(e)
            return 1
        except ValidationError as e:
            print_cli_error(e)
            return 1
        except BackendError as e:
            print_cli_error(e)
            return 1
        except ConnectionError as e:
            print_cli_error(e)
            return 1

        # Envia a mensagem
        try:
            if getattr(args, "stream", False):
                print_stream_chunks(client.stream_generate_message(args.message))
            else:
                response = client.generate_message(args.message)
                print_assistant_response(response)
            return 0
        except AuthError as e:
            print_cli_error(e)
            return 1
        except CLIPermissionError as e:
            print_cli_error(e)
            return 1
        except NotFoundError as e:
            print_cli_error(e)
            return 1
        except ValidationError as e:
            print_cli_error(e)
            return 1
        except BackendError as e:
            print_cli_error(e)
            return 1
        except ConnectionError as e:
            print_cli_error(e)
            return 1

    finally:
        client.close()


def chat_command(args: argparse.Namespace) -> int:
    """
    Executa o comando de chat interativo.

    Args:
        args: Argumentos da linha de comando.

    Returns:
        Código de saída (0 para sucesso, 1 para erro).
    """
    is_valid, error_msg = validate_resume_last_args(args)
    if not is_valid:
        print(error_msg)
        return 1

    api_url = resolve_api_url(args.api_url)
    try:
        token = resolve_interactive_chat_token(args.token)
    except LoginError as e:
        print_cli_error(e)
        return 1
    stream = chat_stream_enabled(args)

    client = CLIClient(api_url)

    try:
        client.set_token(token)

        try:
            user_data = client.validate_token()
            username = user_data.get("username")
        except CLI_HANDLED_ERRORS as e:
            print_cli_error(e)
            return 1

        conversation_id = args.conversation_id
        show_last = args.show_last
        resume_last = getattr(args, "last", False) or getattr(
            args, "resume_last", False
        )

        if resume_last:
            # Tenta obter a conversa mais recente
            try:
                recent_conv_id = get_most_recent_conversation(client)
            except CLI_HANDLED_ERRORS as e:
                print_cli_error(e)
                return 1

            if recent_conv_id:
                client.conversation_id = recent_conv_id
                conversation_id = recent_conv_id
            else:
                # Não há conversas anteriores - cria uma nova
                print_info(
                    "Nenhuma conversa anterior encontrada. "
                    "Criando nova conversa..."
                )
                try:
                    conversation_id = create_chat_conversation(client, chat_title(args))
                except CLI_HANDLED_ERRORS as e:
                    print_cli_error(e)
                    return 1
        elif conversation_id:
            client.conversation_id = conversation_id

            try:
                conversation = client.get_conversation(conversation_id)
                conversation_id = conversation.get("id", conversation_id)
                client.conversation_id = conversation_id
            except CLI_HANDLED_ERRORS as e:
                print_cli_error(e)
                return 1
        else:
            try:
                conversation_id = create_chat_conversation(client, chat_title(args))
            except CLI_HANDLED_ERRORS as e:
                print_cli_error(e)
                return 1

        print_chat_banner(api_url, username, conversation_id, stream)

        # Mostra histórico se --conversation-id foi usado explicitamente
        # ou se --last/--resume-last foi usado e há conversa
        if (args.conversation_id or resume_last) and show_last > 0:
            try:
                print_chat_history(client, show_last)
                print()
            except CLI_HANDLED_ERRORS as e:
                print_cli_error(e, "ao carregar histórico")
                print()

        while True:
            try:
                print_user_label()
                user_input = input()
            except EOFError:
                print("\nAté mais.")
                break
            except KeyboardInterrupt:
                print("\nAté mais.")
                break

            # Normalize input by stripping whitespace
            normalized_input = user_input.strip()

            # Handle slash commands (must be before message generation)
            if normalized_input == "/help":
                print_help()
                continue

            if normalized_input in {"/exit", "/quit"}:
                print("Até mais.")
                break

            if normalized_input == "/history":
                try:
                    print_chat_history(client, show_last)
                except CLI_HANDLED_ERRORS as e:
                    print_cli_error(e, "ao carregar histórico")
                    print()
                continue

            if normalized_input == "/new":
                try:
                    conversation_id = create_chat_conversation(
                        client,
                        chat_title(args),
                    )
                    print_new_conversation_success(conversation_id, chat_title(args))
                except CLI_HANDLED_ERRORS as e:
                    print_cli_error(e, "ao criar nova conversa")
                    print()
                continue

            # Skip empty input after stripping
            if not normalized_input:
                continue

            # Send message to model (only for non-slash commands)
            try:
                if stream:
                    print_streaming_start()
                    print_stream_chunks(client.stream_generate_message(normalized_input))
                    print()
                else:
                    response = client.generate_message(normalized_input)
                    assistant_content = response.get("content", "")
                    print_assistant_message(assistant_content)
                    print()
            except KeyboardInterrupt:
                print("\nMensagem interrompida. Digite /exit para sair.\n")
            except CLI_HANDLED_ERRORS as e:
                print_cli_error(e)
                print()
                continue

    finally:
        client.close()

    return 0


def main() -> int:
    """
    Função principal do CLI.

    Returns:
        Código de saída (0 para sucesso, 1 para erro).
    """
    parser = argparse.ArgumentParser(
        prog="labia-chat",
        description="CLI para chat com modelos locais via backend FastAPI",
        epilog=HELP_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_cli_version()}",
    )

    # Argumentos compartilhados para entrypoint interativo (sem subcomando)
    parser.add_argument(
        "--api-url",
        type=str,
        help=(
            "URL do backend (padrão: http://127.0.0.1:8010, config ou "
            "LABIA_CHAT_API_URL)"
        ),
    )
    parser.add_argument(
        "--token",
        type=str,
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN ou login interativo)",
    )
    parser.add_argument(
        "--title",
        type=str,
        help="Título da nova conversa",
    )
    parser.add_argument(
        "--conversation-id",
        type=str,
        help="ID da conversa para retomar (UUID)",
    )
    parser.add_argument(
        "--last",
        action="store_true",
        help="Retoma a conversa mais recente",
    )
    parser.add_argument(
        "--resume-last",
        action="store_true",
        help="Alias de --last",
    )
    parser.add_argument(
        "--show-last",
        type=int,
        default=10,
        help=(
            "Número de mensagens a exibir no histórico "
            "(padrão: 10, config ou --show-last-default)"
        ),
    )
    chat_stream_group = parser.add_mutually_exclusive_group()
    chat_stream_group.add_argument(
        "--stream",
        action="store_true",
        dest="stream",
        help=argparse.SUPPRESS,
    )
    chat_stream_group.add_argument(
        "--no-stream",
        action="store_false",
        dest="stream",
        help="Usa o endpoint não-streaming legado",
    )
    parser.set_defaults(stream=True)

    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # Comando config
    config_parser = subparsers.add_parser(
        "config",
        help="Gerencia configuração local",
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_command", help="Comandos disponíveis"
    )

    # config init
    config_init_parser = config_subparsers.add_parser(
        "init",
        help="Inicializa ou atualiza a configuração local",
    )
    config_init_parser.add_argument(
        "--api-url",
        type=str,
        help="URL do backend (padrão: http://127.0.0.1:8010)",
    )
    config_init_parser.add_argument(
        "--streaming-default",
        type=str,
        choices=["true", "false"],
        help="Habilitar streaming por padrão (true/false)",
    )
    config_init_parser.add_argument(
        "--show-last-default",
        type=int,
        help="Número de mensagens a exibir por padrão",
    )

    # config show
    config_show_parser = config_subparsers.add_parser(
        "show",
        help="Exibe configuração resolvida do CLI",
    )
    config_show_parser.add_argument(
        "--api-url",
        type=str,
        help="URL do backend (padrão: http://127.0.0.1:8010 ou LABIA_CHAT_API_URL)",
    )
    config_show_parser.add_argument(
        "--token",
        type=str,
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN)",
    )

    # Comando doctor
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Executa diagnósticos do CLI e backend",
    )
    doctor_parser.add_argument(
        "--api-url",
        type=str,
        help="URL do backend (padrão: http://127.0.0.1:8010 ou LABIA_CHAT_API_URL)",
    )
    doctor_parser.add_argument(
        "--token",
        type=str,
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN)",
    )
    doctor_parser.add_argument(
        "--with-model",
        action="store_true",
        help="Também executa POST /chat/model/ping",
    )

    # Comando auth
    auth_parser = subparsers.add_parser(
        "auth",
        help="Comandos de autenticação",
    )
    auth_subparsers = auth_parser.add_subparsers(
        dest="auth_command", help="Comandos disponíveis"
    )

    # auth me
    auth_me_parser = auth_subparsers.add_parser(
        "me",
        help="Valida token e exibe dados do usuário",
    )
    auth_me_parser.add_argument(
        "--api-url",
        type=str,
        help="URL do backend (padrão: http://127.0.0.1:8010 ou LABIA_CHAT_API_URL)",
    )
    auth_me_parser.add_argument(
        "--token",
        type=str,
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN)",
    )

    # Comando conversations
    conversations_parser = subparsers.add_parser(
        "conversations",
        help="Comandos de conversas",
    )
    conversations_subparsers = conversations_parser.add_subparsers(
        dest="conversations_command", help="Comandos disponíveis"
    )

    # conversations create
    conversations_create_parser = conversations_subparsers.add_parser(
        "create",
        help="Cria uma nova conversa",
    )
    conversations_create_parser.add_argument(
        "--api-url",
        type=str,
        help="URL do backend (padrão: http://127.0.0.1:8010 ou LABIA_CHAT_API_URL)",
    )
    conversations_create_parser.add_argument(
        "--token",
        type=str,
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN)",
    )
    conversations_create_parser.add_argument(
        "--title",
        type=str,
        help="Título da nova conversa",
    )

    # conversations list
    conversations_list_parser = conversations_subparsers.add_parser(
        "list",
        help="Lista conversas recentes",
    )
    conversations_list_parser.add_argument(
        "--api-url",
        type=str,
        help="URL do backend (padrão: http://127.0.0.1:8010 ou LABIA_CHAT_API_URL)",
    )
    conversations_list_parser.add_argument(
        "--token",
        type=str,
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN)",
    )
    conversations_list_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Número máximo de conversas a retornar (padrão: 20, máximo: 100)",
    )
    conversations_list_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Número de conversas a pular (padrão: 0)",
    )

    # Comando messages
    messages_parser = subparsers.add_parser(
        "messages",
        help="Comandos de mensagens",
    )
    messages_subparsers = messages_parser.add_subparsers(
        dest="messages_command", help="Comandos disponíveis"
    )

    # messages list
    messages_list_parser = messages_subparsers.add_parser(
        "list",
        help="Lista mensagens de uma conversa",
    )
    messages_list_parser.add_argument(
        "conversation_id",
        type=str,
        help="ID da conversa (UUID)",
    )
    messages_list_parser.add_argument(
        "--api-url",
        type=str,
        help="URL do backend (padrão: http://127.0.0.1:8010 ou LABIA_CHAT_API_URL)",
    )
    messages_list_parser.add_argument(
        "--token",
        type=str,
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN)",
    )
    messages_list_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Número máximo de mensagens a retornar (padrão: 50, máximo: 200)",
    )
    messages_list_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Número de mensagens a pular (padrão: 0)",
    )

    # Comando chat
    chat_parser = subparsers.add_parser(
        "chat",
        help="Comandos de chat",
    )
    chat_subparsers = chat_parser.add_subparsers(
        dest="chat_command", help="Comandos disponíveis"
    )

    # chat send
    chat_send_parser = chat_subparsers.add_parser(
        "send",
        help="Envia uma mensagem não interativa",
    )
    chat_send_parser.add_argument(
        "conversation_id",
        type=str,
        help="ID da conversa (UUID)",
    )
    chat_send_parser.add_argument(
        "message",
        type=str,
        help="Mensagem a ser enviada",
    )
    chat_send_parser.add_argument(
        "--api-url",
        type=str,
        help="URL do backend (padrão: http://127.0.0.1:8010 ou LABIA_CHAT_API_URL)",
    )
    chat_send_parser.add_argument(
        "--token",
        type=str,
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN)",
    )
    chat_send_stream_group = chat_send_parser.add_mutually_exclusive_group()
    chat_send_stream_group.add_argument(
        "--stream",
        action="store_true",
        dest="stream",
        help=argparse.SUPPRESS,
    )
    chat_send_stream_group.add_argument(
        "--no-stream",
        action="store_false",
        dest="stream",
        help="Usa o endpoint não-streaming legado",
    )
    chat_send_parser.set_defaults(stream=True)

    # chat interativo (com argumentos existentes)
    chat_parser.add_argument(
        "--api-url",
        type=str,
        help="URL do backend (padrão: http://127.0.0.1:8010 ou LABIA_CHAT_API_URL)",
    )
    chat_parser.add_argument(
        "--token",
        type=str,
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN ou login interativo)",
    )
    chat_parser.add_argument(
        "--title",
        type=str,
        help="Título da nova conversa",
    )
    chat_parser.add_argument(
        "--conversation-id",
        type=str,
        help="ID da conversa para retomar (UUID)",
    )
    chat_parser.add_argument(
        "--last",
        action="store_true",
        help="Retoma a conversa mais recente",
    )
    chat_parser.add_argument(
        "--resume-last",
        action="store_true",
        help="Alias de --last",
    )
    chat_parser.add_argument(
        "--show-last",
        type=int,
        default=10,
        help="Número de mensagens a exibir no histórico (padrão: 10)",
    )
    chat_stream_group = chat_parser.add_mutually_exclusive_group()
    chat_stream_group.add_argument(
        "--stream",
        action="store_true",
        dest="stream",
        help=argparse.SUPPRESS,
    )
    chat_stream_group.add_argument(
        "--no-stream",
        action="store_false",
        dest="stream",
        help="Usa o endpoint não-streaming legado no chat interativo",
    )
    chat_parser.set_defaults(stream=True)

    args = parser.parse_args()

    if args.command is None:
        # Default to interactive chat REPL
        return chat_command(args)

    if args.command == "config":
        if args.config_command == "show":
            return config_show_command(args)
        elif args.config_command == "init":
            return config_init_command(args)
        else:
            config_parser.print_help()
            return 0

    if args.command == "doctor":
        return doctor_command(args)

    if args.command == "auth":
        if args.auth_command == "me":
            return auth_me_command(args)
        else:
            auth_parser.print_help()
            return 0

    elif args.command == "conversations":
        if args.conversations_command == "create":
            return conversations_create_command(args)
        elif args.conversations_command == "list":
            return conversations_list_command(args)
        else:
            conversations_parser.print_help()
            return 0

    elif args.command == "messages":
        if args.messages_command == "list":
            if not args.conversation_id:
                print("Erro: conversation_id é obrigatório.")
                return 1
            return messages_list_command(args)
        else:
            messages_parser.print_help()
            return 0

    elif args.command == "chat":
        if getattr(args, "chat_command", None) == "send":
            # Valida conversation_id
            if not args.conversation_id:
                print("Erro: conversation_id é obrigatório.")
                return 1
            # Valida message
            if not args.message:
                print("Erro: message é obrigatória.")
                return 1
            return chat_send_command(args)
        elif getattr(args, "chat_command", None) is None:
            # Chat interativo
            if args.show_last < 0:
                print("Erro: --show-last deve ser um número inteiro não negativo.")
                return 2
            return chat_command(args)
        else:
            chat_parser.print_help()
            return 0
