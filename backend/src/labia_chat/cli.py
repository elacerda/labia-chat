"""Entrypoint CLI do labia-chat."""

import argparse
import getpass
import os
import sys
from importlib import metadata
from typing import Any

try:
    import readline
except ImportError:  # pragma: no cover - readline is platform dependent.
    readline: Any | None = None

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
    DEFAULT_API_URL,
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
from labia_chat.cli_session import get_cached_session
from labia_chat.cli_ui import (
    print_assistant_message,
    print_banner,
    print_conversation_history_table,
    print_error,
    print_history_header,
    print_info,
    print_new_conversation_success,
    print_stream_chunks_markdown,
    print_user_message,
)
from labia_chat.cli_ui import (
    print_help as print_help_ui,
)

DEFAULT_CHAT_TITLE = "CLI chat"
MESSAGE_PAGE_SIZE = 200
CONVERSATION_HISTORY_LIMIT = 20
CONVERSATION_TITLE_MAX_LENGTH = 60
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
    Resolve a URL da API na ordem: flag > env > config > default.

    Args:
        args_api_url: Valor passado via --api-url.

    Returns:
        A URL da API resolvida.
    """
    api_url, _source = resolve_api_url_with_source_config(args_api_url)
    return api_url


def resolve_api_url_with_source(args_api_url: str | None) -> tuple[str, str]:
    """
    Resolve a URL da API com a origem detectável.

    Args:
        args_api_url: Valor passado via --api-url.

    Returns:
        Tupla com URL resolvida e origem: argument, env ou default.
    """
    return resolve_api_url_with_source_config(args_api_url)


def resolve_token(
    args_token: str | None,
    allow_interactive_login: bool = False,
) -> str:
    """
    Resolve o token na ordem: flag > env > saved session > prompt.

    Args:
        args_token: Valor passado via --token.
        allow_interactive_login: Se True, permite login interativo AI-Scope
            se nenhum token for encontrado nos estágios anteriores.

    Returns:
        O token resolvido.

    Raises:
        LoginError: Se allow_interactive_login=True e o login for cancelado.
    """
    if args_token:
        return args_token
    env_token = os.environ.get("LABIA_CHAT_TOKEN")
    if env_token:
        return env_token
    # Try saved session
    session_token = get_cached_session()
    if session_token:
        return session_token
    # Only prompt if allow_interactive_login is True
    if allow_interactive_login:
        return prompt_for_ai_scope_login()
    raise LoginError(
        "Token AI-Scope ausente. Informe --token ou LABIA_CHAT_TOKEN. "
        "Login automático só é usado no chat interativo."
    )


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

    Args:
        args_token: Valor passado via --token.

    Returns:
        O token resolvido (via flag, env, session, ou login interativo).
    """
    token = resolve_token(args_token, allow_interactive_login=True)
    # Session tokens from save_session are kept in memory
    # The prompt_for_ai_scope_login returns an in-memory token
    return token


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
    """Resolve whether interactive chat should stream responses."""
    stream, _source = _resolve_streaming(getattr(args, "stream", None))
    return stream


def chat_show_last(args: argparse.Namespace) -> int:
    """Resolve how many recent messages should be shown in chat history."""
    show_last, _source = _resolve_show_last(getattr(args, "show_last", None))
    return show_last


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


def conversation_short_code(conversation_id: str) -> str:
    """Return a compact deterministic conversation code.

    Parameters
    ----------
    conversation_id : str
        Full conversation identifier returned by the backend.

    Returns
    -------
    str
        First eight characters when present, otherwise the original value.
    """
    return conversation_id[:8]


def is_useful_conversation_title(title: str | None) -> bool:
    """Return whether a conversation title is useful for display.

    Parameters
    ----------
    title : str | None
        Conversation title returned by the backend.

    Returns
    -------
    bool
        True when the title has non-generic visible text.
    """
    if title is None:
        return False

    normalized_title = " ".join(title.split())
    return bool(normalized_title) and normalized_title != DEFAULT_CHAT_TITLE


def truncate_conversation_title(
    text: str,
    max_length: int = CONVERSATION_TITLE_MAX_LENGTH,
) -> str:
    """Normalize and truncate text for conversation title display.

    Parameters
    ----------
    text : str
        Source text used as a display title.
    max_length : int, optional
        Maximum number of characters in the returned title.

    Returns
    -------
    str
        Whitespace-normalized title, with ellipsis when truncated.
    """
    normalized_text = " ".join(text.split())
    if len(normalized_text) <= max_length:
        return normalized_text
    if max_length <= 3:
        return "." * max_length
    return f"{normalized_text[: max_length - 3]}..."


def list_all_conversation_messages(
    client: CLIClient,
    conversation_id: str,
    page_size: int = MESSAGE_PAGE_SIZE,
) -> list[dict]:
    """Fetch all messages for a conversation using backend pagination.

    Parameters
    ----------
    client : CLIClient
        Authenticated CLI client used to call the backend.
    conversation_id : str
        Explicit conversation identifier to load.
    page_size : int, optional
        Number of messages requested per backend page.

    Returns
    -------
    list[dict]
        Combined message dictionaries in backend order.

    Raises
    ------
    ValueError
        If ``page_size`` is not positive.
    """
    if page_size <= 0:
        raise ValueError("page_size must be positive")

    messages: list[dict] = []
    offset = 0

    while True:
        page = client.list_messages(
            conversation_id,
            limit=page_size,
            offset=offset,
        )
        if not page:
            break

        messages.extend(page)
        if len(page) < page_size:
            break

        offset += page_size

    return messages


def conversation_display_title(client: CLIClient, conversation: dict) -> str:
    """Build a display title for a conversation without extra message lookups."""
    _ = client

    title = conversation.get("title")
    if is_useful_conversation_title(title):
        return truncate_conversation_title(str(title))

    metadata = conversation.get("metadata")
    if isinstance(metadata, dict):
        for key in (
            "display_title",
            "title",
            "summary",
            "first_user_message",
            "first_user_message_preview",
        ):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return truncate_conversation_title(value)

    return "Conversa sem título"

def build_conversation_history_rows(
    client: CLIClient,
    limit: int = CONVERSATION_HISTORY_LIMIT,
) -> list[dict]:
    """Build data rows for the future conversation history selector.

    Parameters
    ----------
    client : CLIClient
        Authenticated CLI client used to list conversations.
    limit : int, optional
        Maximum number of recent conversations to include.

    Returns
    -------
    list[dict]
        Row dictionaries with index, id, short code, display title, and date.
    """
    conversations = client.list_conversations(limit=limit, offset=0)
    rows: list[dict] = []

    for index, conversation in enumerate(conversations, start=1):
        conversation_id = str(conversation.get("id", ""))
        rows.append(
            {
                "index": index,
                "id": conversation_id,
                "code": conversation_short_code(conversation_id),
                "title": conversation_display_title(client, conversation),
                "updated_at": conversation.get("updated_at")
                or conversation.get("created_at"),
            }
        )

    return rows


def resolve_conversation_history_selection(
    selection: str,
    rows: list[dict],
) -> dict | None:
    """Resolve a history selector entry by number or short code.

    Parameters
    ----------
    selection : str
        Raw user selection from the fallback prompt.
    rows : list[dict]
        Prepared conversation rows.

    Returns
    -------
    dict | None
        Matching row, or None when selection is empty or invalid.
    """
    normalized_selection = selection.strip()
    if not normalized_selection:
        return None

    if normalized_selection.isdigit():
        selected_index = int(normalized_selection)
        for row in rows:
            if row.get("index") == selected_index:
                return row
        return None

    for row in rows:
        if normalized_selection == row.get("code"):
            return row

    return None


def resolve_conversation_history_delete_selection(
    selection: str,
    rows: list[dict],
) -> dict | None:
    """Resolve a remove-from-history command by number or short code.

    Parameters
    ----------
    selection : str
        Raw selection such as ``d 2`` or ``d abc123``.
    rows : list[dict]
        Prepared conversation rows.

    Returns
    -------
    dict | None
        Matching row, or None when the command is invalid.
    """
    parts = selection.strip().split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "d":
        return None
    return resolve_conversation_history_selection(parts[1], rows)


def conversation_history_action(
    action: str,
    row: dict | None = None,
) -> dict:
    """Build a normalized history selector action.

    Parameters
    ----------
    action : str
        Action name: open, remove, or cancel.
    row : dict | None, optional
        Selected conversation row for open/remove actions.

    Returns
    -------
    dict
        Normalized selector action.
    """
    return {"action": action, "row": row}


def format_conversation_history_prompt_rows(
    rows: list[dict],
    selected_index: int,
    selected_ids: set[str] | None = None,
) -> list[tuple[str, str]]:
    """Build prompt-toolkit fragments for conversation history rows.

    Parameters
    ----------
    rows : list[dict]
        Prepared conversation rows.
    selected_index : int
        Zero-based row selected in the prompt-toolkit UI.
    selected_ids : set[str] | None, optional
        Set of selected conversation IDs. If None, treated as empty set.

    Returns
    -------
    list[tuple[str, str]]
        Formatted text fragments for prompt-toolkit.
    """
    if selected_ids is None:
        selected_ids = set()

    fragments = [
        ("class:title", "Histórico de conversas\n"),
        (
            "",
            "Use ↑/↓ para navegar, Space para marcar, "
            "d para remover, q/Esc para sair.\n\n",
        ),
    ]

    for index, row in enumerate(rows):
        is_selected = row.get("id") in selected_ids
        mark = "[x]" if is_selected else "[ ]"
        style = "reverse" if index == selected_index else ""
        pointer = ">" if index == selected_index else " "
        timestamp = row.get("updated_at") or ""
        fragments.append(
            (
                style,
                f"{pointer} {mark} {row.get('index', ''):>2} "
                f"{row.get('code', ''):<8} "
                f"{row.get('title', '')} "
                f"{timestamp}\n",
            )
        )

    return fragments


def conversation_history_removal_targets(
    rows: list[dict],
    selected_index: int,
    selected_ids: set[str],
) -> list[dict]:
    """Return rows to remove based on selection state.

    Parameters
    ----------
    rows : list[dict]
        Prepared conversation rows.
    selected_index : int
        Zero-based row selected in the prompt-toolkit UI.
    selected_ids : set[str]
        Set of selected conversation IDs.

    Returns
    -------
    list[dict]
        Rows to remove. Returns marked rows if any, otherwise the highlighted row.
    """
    if selected_ids:
        return [row for row in rows if row.get("id") in selected_ids]
    return [rows[selected_index]]


def confirm_conversation_history_removal(rows: list[dict]) -> bool:
    """Ask for confirmation before removing conversation(s).

    Parameters
    ----------
    rows : list[dict]
        Rows to be removed.

    Returns
    -------
    bool
        True if user typed exactly 'apagar', False otherwise.
    """
    count = len(rows)
    if count == 1:
        print_info("Remover 1 conversa do histórico?")
    else:
        print_info(f"Remover {count} conversas do histórico?")
    confirmation = input("Digite 'apagar' para confirmar; Enter cancela: ")
    return confirmation == "apagar"


def remove_conversation_history_rows(
    client: CLIClient, rows: list[dict]
) -> tuple[list[dict], list[dict]]:
    """Archive multiple conversations and return removed/failed rows.

    Parameters
    ----------
    client : CLIClient
        Authenticated CLI client.
    rows : list[dict]
        Rows to remove.

    Returns
    -------
    tuple[list[dict], list[dict]]
        Tuple of (removed_rows, failed_rows).
    """
    removed_rows: list[dict] = []
    failed_rows: list[dict] = []

    for row in rows:
        conversation_id = str(row.get("id", ""))
        try:
            client.archive_conversation(conversation_id)
            removed_rows.append(row)
        except Exception:
            failed_rows.append(row)

    return removed_rows, failed_rows


def prompt_conversation_history_action(
    rows: list[dict],
    selected_ids: set[str] | None = None,
) -> dict:
    """Select a history action using prompt-toolkit key bindings.

    Parameters
    ----------
    rows : list[dict]
        Prepared conversation rows.
    selected_ids : set[str] | None, optional
        Set of selected conversation IDs. If None, treated as empty set.

    Returns
    -------
    dict
        Selector action for open, remove, or cancel.
    """
    if selected_ids is None:
        selected_ids_set: set[str] = set()
    else:
        selected_ids_set = selected_ids

    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.controls import FormattedTextControl

    selected_index = 0
    key_bindings = KeyBindings()

    def get_text_fragments() -> list[tuple[str, str]]:
        return format_conversation_history_prompt_rows(
            rows, selected_index, selected_ids_set
        )

    control = FormattedTextControl(get_text_fragments)

    @key_bindings.add("up")
    def _(event) -> None:
        nonlocal selected_index
        selected_index = max(0, selected_index - 1)
        event.app.invalidate()

    @key_bindings.add("down")
    def _(event) -> None:
        nonlocal selected_index
        selected_index = min(len(rows) - 1, selected_index + 1)
        event.app.invalidate()

    @key_bindings.add("space")
    def _(event) -> None:
        nonlocal selected_index, selected_ids_set
        row_id = rows[selected_index].get("id")
        if isinstance(row_id, str):
            if row_id in selected_ids_set:
                selected_ids_set.discard(row_id)
            else:
                selected_ids_set.add(row_id)
        event.app.invalidate()

    @key_bindings.add("enter")
    def _(event) -> None:
        event.app.exit(result=conversation_history_action("open", rows[selected_index]))

    @key_bindings.add("d")
    def _(event) -> None:
        targets = conversation_history_removal_targets(
            rows, selected_index, selected_ids_set
        )
        event.app.exit(
            result={
                "action": "remove",
                "row": targets[0] if targets else None,
                "rows": targets,
            }
        )

    @key_bindings.add("q")
    @key_bindings.add("escape")
    def _(event) -> None:
        event.app.exit(result=conversation_history_action("cancel"))

    application = Application(
        layout=Layout(Window(content=control)),
        key_bindings=key_bindings,
        full_screen=False,
    )
    return application.run()


def prompt_conversation_history_row(rows: list[dict]) -> dict | None:
    """Select a conversation row using prompt-toolkit key bindings."""
    action = prompt_conversation_history_action(rows)
    if action.get("action") == "open":
        return action.get("row")
    return None


def prompt_conversation_history_action_fallback(rows: list[dict]) -> dict:
    """Select a history action using plain input().

    Parameters
    ----------
    rows : list[dict]
        Prepared conversation rows.

    Returns
    -------
    dict
        Selector action for open, remove, or cancel.
    """
    print_conversation_history_table(rows)
    selection = input(
        "Escolha pelo número/código; use d <número/código> para remover; "
        "Enter cancela: "
    )
    if not selection.strip():
        return conversation_history_action("cancel")

    row_to_remove = resolve_conversation_history_delete_selection(selection, rows)
    if row_to_remove is not None:
        return conversation_history_action("remove", row_to_remove)

    row_to_open = resolve_conversation_history_selection(selection, rows)
    if row_to_open is not None:
        return conversation_history_action("open", row_to_open)

    return conversation_history_action("cancel")


def prompt_conversation_history_row_fallback(rows: list[dict]) -> dict | None:
    """Select a conversation row using plain input()."""
    action = prompt_conversation_history_action_fallback(rows)
    if action.get("action") == "open":
        return action.get("row")
    return None


def select_conversation_history_action(
    rows: list[dict],
    prefer_interactive: bool = False,
) -> dict:
    """Select one action from prepared conversation history data.

    Parameters
    ----------
    rows : list[dict]
        Prepared conversation rows.
    prefer_interactive : bool, optional
        Try the prompt-toolkit selector even when stdin is not a TTY.

    Returns
    -------
    dict
        Selector action for open, remove, or cancel.
    """
    if not rows:
        print_info("Nenhuma conversa encontrada.")
        return conversation_history_action("cancel")

    if prefer_interactive or sys.stdin.isatty():
        try:
            return prompt_conversation_history_action(rows)
        except Exception as exc:  # noqa: BLE001
            print_info(
                "Seletor interativo indisponível "
                f"({type(exc).__name__}: {exc}). "
                "Usando seleção por número/código."
            )

    return prompt_conversation_history_action_fallback(rows)


def select_conversation_history_row(rows: list[dict]) -> dict | None:
    """Select one row from prepared conversation history data."""
    action = select_conversation_history_action(rows)
    if action.get("action") == "open":
        return action.get("row")
    return None


def open_conversation_history_row(client: CLIClient, row: dict) -> None:
    """Open a selected conversation and print its full messages.

    Parameters
    ----------
    client : CLIClient
        Authenticated CLI client.
    row : dict
        Selected conversation history row.
    """
    conversation_id = str(row.get("id", ""))
    client.conversation_id = conversation_id
    print_info(
        f"Conversa selecionada: {row.get('code', '')} — "
        f"{row.get('title', '')}"
    )

    messages = list_all_conversation_messages(client, conversation_id)
    if not messages:
        print_info("Nenhuma mensagem ainda.")
        return

    print_messages(messages, len(messages))


def remove_conversation_history_row(client: CLIClient, row: dict) -> bool:
    """Archive a selected conversation after explicit confirmation.

    Parameters
    ----------
    client : CLIClient
        Authenticated CLI client.
    row : dict
        Selected conversation history row.

    Returns
    -------
    bool
        True when the conversation was archived, False when cancelled.
    """
    conversation_id = str(row.get("id", ""))
    print_info(
        f"Remover do histórico: {row.get('code', '')} — "
        f"{row.get('title', '')}"
    )
    confirmation = input(
        'Digite "apagar" para remover esta conversa do histórico; Enter cancela: '
    )
    if confirmation != "apagar":
        print_info("Remoção cancelada.")
        return False

    client.archive_conversation(conversation_id)
    if client.conversation_id == conversation_id:
        client.conversation_id = None
        print_info(
            "A conversa atual foi removida do histórico. "
            "Crie uma nova conversa com /new ou selecione outra com /history."
        )
    print_info("Conversa removida do histórico.")
    return True



def drop_conversation_history_row(
    rows: list[dict],
    conversation_id: str,
) -> list[dict]:
    """Remove a conversation row and reindex the remaining history rows."""
    kept_rows: list[dict] = []

    for index, row in enumerate(
        (row for row in rows if row.get("id") != conversation_id),
        start=1,
    ):
        kept_row = dict(row)
        kept_row["index"] = index
        kept_rows.append(kept_row)

    return kept_rows

def handle_conversation_history(
    client: CLIClient,
    prompt_session: Any | None = None,
) -> None:
    """Open the interactive conversation history selector.

    Parameters
    ----------
    client : CLIClient
        Authenticated CLI client used to list and open conversations.
    prompt_session : Any | None, optional
        Active chat prompt session, when running in the interactive chat.
    """
    rows = build_conversation_history_rows(client, CONVERSATION_HISTORY_LIMIT)
    if not rows:
        print_info("Nenhuma conversa encontrada.")
        return

    while rows:
        action = select_conversation_history_action(
            rows,
            prefer_interactive=prompt_session is not None,
        )
        action_name = action.get("action")
        selected_row = action.get("row")

        if action_name == "open" and selected_row is not None:
            try:
                open_conversation_history_row(client, selected_row)
            except CLI_HANDLED_ERRORS as exc:
                print_cli_error(exc, "ao abrir conversa")
                print()
                continue
            return

        if action_name == "remove":
            target_rows = action.get("rows") or (
                [selected_row] if selected_row is not None else []
            )
            if not target_rows:
                continue

            if not confirm_conversation_history_removal(target_rows):
                print_info("Remoção cancelada.")
                continue

            removed, failed = remove_conversation_history_rows(client, target_rows)

            if removed:
                removed_ids = {
                    str(row.get("id") or "")
                    for row in removed
                    if row.get("id")
                }
                rows = drop_conversation_history_rows(rows, removed_ids)
                if not rows:
                    print_info("Nenhuma conversa encontrada.")
                    return

            for failed_row in failed:
                print_error(
                    "Falha ao remover conversa: "
                    f"{failed_row.get('code', '')} — {failed_row.get('title', '')}"
                )

            continue

        return


def drop_conversation_history_rows(
    rows: list[dict],
    conversation_ids: set[str],
) -> list[dict]:
    """Remove multiple conversation rows and reindex the remaining history rows.

    Parameters
    ----------
    rows : list[dict]
        Current conversation history rows.
    conversation_ids : set[str]
        IDs of conversations to remove.

    Returns
    -------
    list[dict]
        New list of rows with removed IDs dropped and reindexed.
    """
    kept_rows: list[dict] = []

    for row in rows:
        if row.get("id") not in conversation_ids:
            kept_row = dict(row)
            kept_row["index"] = len(kept_rows) + 1
            kept_rows.append(kept_row)

    return kept_rows


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


def enable_interactive_line_editing() -> None:
    """Enable terminal line editing for input() when readline is available."""
    if readline is None:
        return

    readline.set_history_length(1000)


def create_chat_prompt_session() -> Any | None:
    """Create the richer chat prompt when running in an interactive terminal."""
    if not sys.stdin.isatty():
        return None

    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.key_binding import KeyBindings
    except ImportError:
        return None

    key_bindings = KeyBindings()

    @key_bindings.add("enter")
    def _(event) -> None:
        event.app.exit(result=event.app.current_buffer.text)

    @key_bindings.add("c-j")
    def _(event) -> None:
        event.current_buffer.insert_text("\n")

    @key_bindings.add("escape", "enter")
    def _(event) -> None:
        event.current_buffer.insert_text("\n")

    return PromptSession(
        key_bindings=key_bindings,
        multiline=True,
        prompt_continuation="... ",
    )


def read_chat_input(prompt_session: Any | None) -> str:
    """Read one chat message from the terminal."""
    if prompt_session is None:
        return input("Você: ")
    return prompt_session.prompt("Você: ")


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
    """Imprime chunks de streaming como Markdown renderizado."""
    print_stream_chunks_markdown(chunks)


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
    from labia_chat.cli_auth import LoginError

    api_url = resolve_api_url(args.api_url)
    try:
        token = resolve_token(args.token, allow_interactive_login=True)
    except LoginError as e:
        print_cli_error(e)
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


def auth_login_command(args: argparse.Namespace) -> int:
    """
    Executa o comando 'auth login' para autenticar e salvar sessão.

    Args:
        args: Argumentos da linha de comando.

    Returns:
        Código de saída (0 para sucesso, 1 para erro).
    """
    from labia_chat.cli_auth import (
        LoginError,
        store_session_after_login,
    )
    from labia_chat.cli_client import CLIClient

    api_url = resolve_api_url(args.api_url)

    try:
        username, password = _prompt_for_credentials()
        token = login_ai_scope_with_api_url(username, password, api_url)
    except LoginError as e:
        print_cli_error(e)
        return 1

    # Store the session
    store_session_after_login(token, username, api_url)

    # Validate and print user summary
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


def _prompt_for_credentials() -> tuple[str, str]:
    """
    Solicita credenciais AI-Scope.

    Returns:
        Tupla (username, password).
    """
    username = input("AI-Scope username: ").strip()
    if not username:
        raise LoginError("Usuário AI-Scope não informado.")
    password = getpass.getpass("AI-Scope password: ")
    if not password:
        raise LoginError("Senha AI-Scope não informada.")
    return username, password


def login_ai_scope_with_api_url(
    username: str,
    password: str,
    api_url: str,
) -> str:
    """
    Realiza login AI-Scope e retorna o access_token.

    Args:
        username: Nome de usuário AI-Scope.
        password: Senha AI-Scope.
        api_url: URL da API (usada para diagnose em erros).

    Returns:
        Access token retornado pelo AI-Scope.

    Raises:
        LoginError: Se o login falhar.
    """
    from labia_chat.cli_auth import AI_SCOPE_LOGIN_URL, login_ai_scope

    # Use the fixed AI-Scope login URL (not the api_url)
    return login_ai_scope(
        username,
        password,
        login_url=AI_SCOPE_LOGIN_URL,
    )


def auth_logout_command(args: argparse.Namespace) -> int:
    """
    Executa o comando 'auth logout' para limpar sessão salva.

    Args:
        args: Argumentos da linha de comando (ignorados).

    Returns:
        Código de saída (0 para sucesso, 1 para erro).
    """
    from labia_chat.cli_session import clear_session

    clear_session()
    print_info("Sessão limpa. Você precisará fazer login novamente.")
    return 0


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
                print_stream_chunks_markdown(
                    client.stream_generate_message(args.message)
                )
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

    show_last = chat_show_last(args)
    if show_last < 0:
        print("Erro: --show-last deve ser um número inteiro não negativo.")
        return 2

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

        enable_interactive_line_editing()
        prompt_session = create_chat_prompt_session()

        while True:
            try:
                user_input = read_chat_input(prompt_session)
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
                    handle_conversation_history(client, prompt_session)
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
                    print_stream_chunks_markdown(
                        client.stream_generate_message(normalized_input)
                    )
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
    api_url_help = (
        f"URL do backend (padrão: {DEFAULT_API_URL}, config ou LABIA_CHAT_API_URL)"
    )

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
        help=api_url_help,
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
        default=None,
        help=(
            "Número de mensagens a exibir no histórico "
            "(padrão: config ou 10)"
        ),
    )
    chat_stream_group = parser.add_mutually_exclusive_group()
    chat_stream_group.add_argument(
        "--stream",
        action="store_true",
        dest="stream",
        default=None,
        help=argparse.SUPPRESS,
    )
    chat_stream_group.add_argument(
        "--no-stream",
        action="store_false",
        dest="stream",
        default=None,
        help="Usa o endpoint não-streaming legado",
    )

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
        help=f"URL do backend a salvar (padrão embutido: {DEFAULT_API_URL})",
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
        help=api_url_help,
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
        help=api_url_help,
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
        help=api_url_help,
    )
    auth_me_parser.add_argument(
        "--token",
        type=str,
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN)",
    )

    # auth login
    auth_login_parser = auth_subparsers.add_parser(
        "login",
        help="Faz login AI-Scope e salva sessão localmente",
    )
    auth_login_parser.add_argument(
        "--api-url",
        type=str,
        help=api_url_help,
    )

    # auth logout
    auth_subparsers.add_parser(
        "logout",
        help="Limpa sessão local salva",
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
        help=api_url_help,
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
        help=api_url_help,
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
        help=api_url_help,
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
        help=api_url_help,
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
        help=api_url_help,
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
        default=None,
        help="Número de mensagens a exibir no histórico (padrão: config ou 10)",
    )
    chat_stream_group = chat_parser.add_mutually_exclusive_group()
    chat_stream_group.add_argument(
        "--stream",
        action="store_true",
        dest="stream",
        default=None,
        help=argparse.SUPPRESS,
    )
    chat_stream_group.add_argument(
        "--no-stream",
        action="store_false",
        dest="stream",
        default=None,
        help="Usa o endpoint não-streaming legado no chat interativo",
    )

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
        elif args.auth_command == "login":
            return auth_login_command(args)
        elif args.auth_command == "logout":
            return auth_logout_command(args)
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
            if args.show_last is not None and args.show_last < 0:
                print("Erro: --show-last deve ser um número inteiro não negativo.")
                return 2
            return chat_command(args)
        else:
            chat_parser.print_help()
            return 0
