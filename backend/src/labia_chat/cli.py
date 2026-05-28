"""Entrypoint CLI do labia-chat."""

import argparse
import getpass
import os

from labia_chat.cli_client import (
    AuthError,
    BackendError,
    CLIClient,
    ConnectionError,
    NotFoundError,
    PermissionError,
)


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
    return "http://127.0.0.1:8010"


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


def print_help() -> None:
    """Imprime a ajuda dos comandos disponíveis."""
    print("\nComandos disponíveis:")
    print("  /help    Mostra esta mensagem de ajuda")
    print("  /exit    Sai do chat")
    print("  /history Mostra o histórico da conversa")
    print("  (qualquer outra linha envia uma mensagem)")
    print()


def print_messages(messages: list[dict], show_last: int) -> None:
    """
    Imprime as últimas N mensagens.

    Args:
        messages: Lista de mensagens.
        show_last: Número de mensagens a exibir.
    """
    if not messages:
        print("Nenhuma mensagem ainda.")
        return

    # Pega as últimas N mensagens
    last_messages = messages[-show_last:]

    for msg in last_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        # Formata a role para exibição
        if role == "user":
            print(f"Você: {content}")
        elif role == "assistant":
            print(f"Assistente: {content}")
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
    token = resolve_token(args.token)

    client = CLIClient(api_url)

    try:
        client.set_token(token)
        user_data = client.validate_token()
        print_user_summary(user_data)
        return 0
    except AuthError as e:
        print(f"Erro: {e}")
        return 1
    except PermissionError as e:
        print(f"Erro: {e}")
        return 1
    except BackendError as e:
        print(f"Erro: {e}")
        return 1
    except ConnectionError as e:
        print(f"Erro: {e}")
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
    token = resolve_token(args.token)

    client = CLIClient(api_url)

    try:
        client.set_token(token)
        title = args.title if args.title else None
        conversation = client.create_conversation(title=title)
        print_conversation_summary(conversation)
        return 0
    except AuthError as e:
        print(f"Erro: {e}")
        return 1
    except PermissionError as e:
        print(f"Erro: {e}")
        return 1
    except BackendError as e:
        print(f"Erro: {e}")
        return 1
    except ConnectionError as e:
        print(f"Erro: {e}")
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
    token = resolve_token(args.token)

    client = CLIClient(api_url)

    try:
        client.set_token(token)
        conversations = client.list_conversations()
        print_conversations_list(conversations)
        return 0
    except AuthError as e:
        print(f"Erro: {e}")
        return 1
    except PermissionError as e:
        print(f"Erro: {e}")
        return 1
    except BackendError as e:
        print(f"Erro: {e}")
        return 1
    except ConnectionError as e:
        print(f"Erro: {e}")
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
    token = resolve_token(args.token)

    client = CLIClient(api_url)

    try:
        client.set_token(token)
        messages = client.list_messages(args.conversation_id)
        print_messages_list(messages)
        return 0
    except AuthError as e:
        print(f"Erro: {e}")
        return 1
    except PermissionError as e:
        print(f"Erro: {e}")
        return 1
    except NotFoundError as e:
        print(f"Erro: {e}")
        return 1
    except BackendError as e:
        print(f"Erro: {e}")
        return 1
    except ConnectionError as e:
        print(f"Erro: {e}")
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
    token = resolve_token(args.token)

    client = CLIClient(api_url)

    try:
        client.set_token(token)
        client.conversation_id = args.conversation_id

        # Valida o token primeiro
        try:
            client.validate_token()
        except AuthError as e:
            print(f"Erro: {e}")
            return 1
        except PermissionError as e:
            print(f"Erro: {e}")
            return 1
        except BackendError as e:
            print(f"Erro: {e}")
            return 1
        except ConnectionError as e:
            print(f"Erro: {e}")
            return 1

        # Envia a mensagem
        try:
            response = client.generate_message(args.message)
            print_assistant_response(response)
            return 0
        except AuthError as e:
            print(f"Erro: {e}")
            return 1
        except PermissionError as e:
            print(f"Erro: {e}")
            return 1
        except NotFoundError as e:
            print(f"Erro: {e}")
            return 1
        except BackendError as e:
            print(f"Erro: {e}")
            return 1
        except ConnectionError as e:
            print(f"Erro: {e}")
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
    api_url = resolve_api_url(args.api_url)
    token = resolve_token(args.token)

    client = CLIClient(api_url)

    try:
        # Define o token
        client.set_token(token)

        # Valida o token
        try:
            user_data = client.validate_token()
            username = user_data.get("username", "usuário")
            print(f"Autenticado como: {username}\n")
        except AuthError as e:
            print(f"Erro: {e}")
            return 1
        except PermissionError as e:
            print(f"Erro: {e}")
            return 1
        except BackendError as e:
            print(f"Erro: {e}")
            return 1
        except ConnectionError as e:
            print(f"Erro: {e}")
            return 1

        # Verifica se deve resumir uma conversa existente
        conversation_id = args.conversation_id
        show_last = args.show_last

        if conversation_id:
            # Resumir conversa existente
            client.conversation_id = conversation_id

            try:
                # Valida que a conversa existe e pertence ao usuário
                conversation = client.get_conversation(conversation_id)
                conv_title = conversation.get("title", "Sem título")
                print(f"Conversa retomada: {conversation_id}")
                if conv_title:
                    print(f"Título: {conv_title}")
                print()
            except AuthError as e:
                print(f"Erro: {e}")
                return 1
            except PermissionError as e:
                print(f"Erro: {e}")
                return 1
            except NotFoundError as e:
                print(f"Erro: {e}")
                return 1
            except BackendError as e:
                print(f"Erro: {e}")
                return 1
            except ConnectionError as e:
                print(f"Erro: {e}")
                return 1

            # Se show_last > 0, exibe as últimas mensagens
            if show_last > 0:
                try:
                    messages = client.list_messages(conversation_id)
                    print(f"Últimas {min(show_last, len(messages))} mensagens:")
                    print_messages(messages, show_last)
                except AuthError as e:
                    print(f"Erro ao carregar histórico: {e}")
                except PermissionError as e:
                    print(f"Erro ao carregar histórico: {e}")
                except NotFoundError as e:
                    print(f"Erro ao carregar histórico: {e}")
                except BackendError as e:
                    print(f"Erro ao carregar histórico: {e}")
                except ConnectionError as e:
                    print(f"Erro ao carregar histórico: {e}")
                print()

            print("Digite /help para ver os comandos disponíveis.\n")
        else:
            # Cria nova conversa (comportamento original MVP 2.11)
            title = args.title if args.title else None
            try:
                conversation = client.create_conversation(title=title)
                conv_id = conversation.get("id", "desconhecido")
                print(f"Nova conversa criada: {conv_id}")
                print("Digite /help para ver os comandos disponíveis.\n")
            except AuthError as e:
                print(f"Erro: {e}")
                return 1
            except PermissionError as e:
                print(f"Erro: {e}")
                return 1
            except BackendError as e:
                print(f"Erro: {e}")
                return 1
            except ConnectionError as e:
                print(f"Erro: {e}")
                return 1

        # Loop interativo
        while True:
            try:
                user_input = input("Você: ")
            except EOFError:
                print("\nSaindo...")
                break

            # Trata comandos
            if user_input == "/help":
                print_help()
                continue

            if user_input == "/exit":
                print("Saindo...")
                break

            if user_input == "/history":
                if not client.conversation_id:
                    print("Erro: Nenhuma conversa selecionada.\n")
                    continue
                try:
                    messages = client.list_messages(client.conversation_id)
                    print(f"Últimas {min(show_last, len(messages))} mensagens:")
                    print_messages(messages, show_last)
                except AuthError as e:
                    print(f"Erro ao carregar histórico: {e}\n")
                except PermissionError as e:
                    print(f"Erro ao carregar histórico: {e}\n")
                except NotFoundError as e:
                    print(f"Erro ao carregar histórico: {e}\n")
                except BackendError as e:
                    print(f"Erro ao carregar histórico: {e}\n")
                except ConnectionError as e:
                    print(f"Erro ao carregar histórico: {e}\n")
                continue

            # Envia mensagem normal
            if not user_input.strip():
                # Linha vazia apenas repete o prompt
                continue

            try:
                response = client.generate_message(user_input)
                assistant_content = response.get("content", "")
                print(f"Assistente: {assistant_content}\n")
            except AuthError as e:
                print(f"Erro: {e}\n")
                break
            except PermissionError as e:
                print(f"Erro: {e}\n")
                break
            except NotFoundError as e:
                print(f"Erro: {e}\n")
                break
            except BackendError as e:
                print(f"Erro: {e}\n")
                break
            except ConnectionError as e:
                print(f"Erro: {e}\n")
                break

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
    )

    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

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
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN ou prompt sem eco)",
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
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN ou prompt sem eco)",
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
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN ou prompt sem eco)",
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
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN ou prompt sem eco)",
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
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN ou prompt sem eco)",
    )

    # chat interativo (com argumentos existentes)
    chat_parser.add_argument(
        "--api-url",
        type=str,
        help="URL do backend (padrão: http://127.0.0.1:8010 ou LABIA_CHAT_API_URL)",
    )
    chat_parser.add_argument(
        "--token",
        type=str,
        help="Token AI-Scope (padrão: LABIA_CHAT_TOKEN ou prompt sem eco)",
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
        "--show-last",
        type=int,
        default=10,
        help="Número de mensagens a exibir no histórico (padrão: 10)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

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
                return 1
            return chat_command(args)
        else:
            chat_parser.print_help()
            return 0
