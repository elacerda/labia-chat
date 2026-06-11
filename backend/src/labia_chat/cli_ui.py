"""Helper module for CLI terminal styling using Rich."""

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# Custom theme for consistent styling
CLI_THEME = Theme(
    {
        "user": "bold cyan",
        "assistant": "bold green",
        "system": "bold yellow",
        "error": "bold red",
        "suggestion": "bold magenta",
        "info": "bold blue",
        "banner": "bold cyan",
        "banner_title": "bold white on cyan",
        "banner_subtle": "dim white",
        "success": "bold green",
    }
)

# Create a console instance with auto-detection for color support.
console = Console(theme=CLI_THEME)


def print_banner(
    api_url: str,
    username: str | None,
    conversation_id: str,
    stream: bool,
) -> None:
    """
    Print the interactive chat banner with visual polish.

    Args:
        api_url: The API URL being used.
        username: The authenticated username, if available.
        conversation_id: The current conversation ID.
        stream: Se o streaming está ativo.
    """
    # Build the banner content
    lines = [
        Text.from_markup("[banner]labia-chat[/banner]"),
        Text.from_markup(
            f"  [banner_subtle]API URL:[/banner_subtle] "
            f"[info]{api_url}[/info]"
        ),
    ]

    if username:
        lines.append(
            Text.from_markup(
                f"  [banner_subtle]Usuário:[/banner_subtle] "
                f"[info]{username}[/info]"
            )
        )

    lines.extend([
        Text.from_markup(
            f"  [banner_subtle]ID da conversa:[/banner_subtle] "
            f"[info]{conversation_id}[/info]"
        ),
        Text.from_markup(
            f"  [banner_subtle]Streaming:[/banner_subtle] "
            f"[info]{'ativo' if stream else 'desativado'}[/info]"
        ),
        Text.from_markup(""),
        Text.from_markup(
            "[banner_subtle]Digite /help para comandos ou "
            "/exit para sair.[/banner_subtle]"
        ),
    ])

    # Print with a panel
    console.print(Panel(
        Group(*lines),
        title="[banner_title]labia-chat[/banner_title]",
        title_align="left",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print()


def print_user_label() -> None:
    """Print the user label prefix."""
    console.print("[user]Você[/user]: ", end="")


def print_assistant_label() -> None:
    """Print the assistant label prefix."""
    console.print("[assistant]Assistente[/assistant]: ", end="")


def print_system_label() -> None:
    """Print the system label prefix."""
    console.print("[system]Sistema[/system]: ", end="")


def print_error_label() -> None:
    """Print the error label prefix."""
    console.print("[error]Erro[/error]: ", end="")


def print_suggestion_label() -> None:
    """Print the suggestion label prefix."""
    console.print("[suggestion]Sugestão[/suggestion]: ", end="")


def print_help() -> None:
    """Print the help message with improved formatting."""
    console.print()
    console.print(Text("Comandos disponíveis", style="info"))

    table = Table.grid(padding=(0, 3))
    table.add_column(style="user", no_wrap=True)
    table.add_column()

    table.add_row("/help", "Mostra esta ajuda")
    table.add_row("/history", "Mostra o histórico de conversas")
    table.add_row("/new", "Cria uma nova conversa e muda para ela")
    table.add_row("/exit", "Sai do chat")
    table.add_row("/quit", "Sai do chat")
    table.add_row("Enter", "Envia a mensagem")
    table.add_row("Ctrl-J / Esc+Enter", "Insere nova linha antes de enviar")
    table.add_row("qualquer outro texto", "Envia uma mensagem ao assistente")

    console.print(table)
    console.print()
    console.print(Text("Exemplos", style="info"))
    console.print("  Digite sua mensagem e pressione Enter para enviar")
    console.print("  Use Ctrl-J ou Esc+Enter para escrever mensagens multilinha")
    console.print("  Use /new para começar uma nova conversa")
    console.print("  Use /history para revisar mensagens recentes")
    console.print()


def print_history_header(count: int) -> None:
    """Print a header for the history display."""
    console.print()
    console.print(
        Panel(
            f"[info]Exibindo últimas [bold]{count}[/bold] mensagens[/info]",
            border_style="blue",
            padding=(0, 2),
        )
    )
    console.print()


def print_conversation_history_table(rows: list[dict]) -> None:
    """Print conversation-history rows for selection.

    Parameters
    ----------
    rows : list[dict]
        Prepared conversation rows with index, code, title, and timestamp.
    """
    console.print()
    console.print(Text("Histórico de conversas", style="info"))
    console.print("Use ↑/↓ e Enter para abrir, q/Esc para sair.")

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("#", justify="right", no_wrap=True)
    table.add_column("Código", no_wrap=True)
    table.add_column("Título")
    table.add_column("Atualizada", no_wrap=True)

    for row in rows:
        table.add_row(
            str(row.get("index", "")),
            str(row.get("code", "")),
            str(row.get("title", "")),
            str(row.get("updated_at") or ""),
        )

    console.print(table)
    console.print()


def print_new_conversation_success(
    conversation_id: str, title: str | None = None
) -> None:
    """Print success message for creating a new conversation."""
    console.print()
    console.print(
        Panel(
            f"[success]Nova conversa criada[/success]\n"
            f"  [info]ID:[/info] [bold]{conversation_id}[/bold]"
            + (f"\n  [info]Título:[/info] {title}" if title else ""),
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()


def print_error(message: str) -> None:
    """Print an error message."""
    console.print()
    console.print(
        Panel(f"[error]{message}[/error]", border_style="red", padding=(0, 2))
    )
    console.print()


def print_info(message: str) -> None:
    """Print an info message."""
    console.print()
    console.print(Panel(f"[info]{message}[/info]", border_style="blue", padding=(0, 2)))
    console.print()


def print_suggestion(message: str) -> None:
    """Print a suggestion message."""
    console.print()
    console.print(
        Panel(
            f"[suggestion]{message}[/suggestion]",
            border_style="magenta",
            padding=(0, 2),
        )
    )
    console.print()


def print_user_message(content: str) -> None:
    """Print a user message with proper styling."""
    console.print()
    console.print(Panel(content, border_style="cyan", padding=(0, 2)))
    console.print()


def build_assistant_markdown_panel(
    content: str, title: str | None = None
) -> Panel:
    """Build a Markdown panel for assistant output.

    Parameters
    ----------
    content : str
        Markdown content rendered inside the panel.
    title : str | None, optional
        Optional Rich markup title displayed on the panel.

    Returns
    -------
    Panel
        Rich panel configured for assistant Markdown output.
    """
    title_options = {}
    if title is not None:
        title_options = {"title": title, "title_align": "left"}

    return Panel(
        Markdown(content),
        border_style="green",
        padding=(0, 2),
        safe_box=True,
        **title_options,
    )


def print_assistant_message(content: str) -> None:
    """Print an assistant message with proper styling."""
    console.print()
    console.print(build_assistant_markdown_panel(content))
    console.print()


def print_stream_chunks_markdown(chunks) -> None:
    """Print streaming assistant chunks as progressively rendered Markdown."""
    content = ""
    panel_title = "[assistant]Assistente[/assistant]"

    with Live(console=console, refresh_per_second=12, transient=True) as live:
        for chunk in chunks:
            content += chunk
            live.update(
                build_assistant_markdown_panel(content, title=panel_title),
                refresh=True,
            )

    console.print(build_assistant_markdown_panel(content, title=panel_title))
    console.print()


def print_diagnostic(status: str, label: str, detail: str = "") -> None:
    """
    Print a diagnostic line with status indicator.

    Args:
        status: Status indicator (ok, fail, skip).
        label: The diagnostic label.
        detail: Optional detail text.
    """
    status_styles = {
        "ok": "green",
        "fail": "red",
        "skip": "yellow",
    }
    style = status_styles.get(status, "white")
    status_marker = (
        "[ok]" if status == "ok"
        else "[fail]" if status == "fail"
        else "[skip]"
    )
    status_style = "ok" if status == "ok" else "fail" if status == "fail" else "skip"
    line = f"[{style}]{status_marker}[/{status_style}] {label}"
    if detail:
        line = f"{line}: {detail}"
    console.print(line)


def print_messages_list(messages: list[dict]) -> None:
    """
    Print a list of messages with visual distinction.

    Args:
        messages: List of message dictionaries.
    """
    if not messages:
        console.print("[info]Nenhuma mensagem ainda.[/info]")
        return

    console.print(f"[info]Total de mensagens: [bold]{len(messages)}[/bold][/info]")
    console.print()

    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        # Format role with appropriate style
        role_styles = {
            "user": "user",
            "assistant": "assistant",
            "system": "system",
        }
        role_style = role_styles.get(role, "info")
        role_display = role.upper() if role in ("user", "assistant", "system") else role

        role_end = (
            "user" if role == "user"
            else "assistant" if role == "assistant"
            else "system"
        )
        console.print(f"[{role_style}][{role_display}][/{role_end}]: {content}")
        console.print()
