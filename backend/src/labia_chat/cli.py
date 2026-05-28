"""Entrypoint CLI do labia-chat."""

import argparse
import getpass
import os
import sys

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
    print("  (qualquer outra linha envia uma mensagem)")
    print()


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

        # Cria a conversa
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

    # Comando chat
    chat_parser = subparsers.add_parser(
        "chat",
        help="Inicia o chat interativo",
    )
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

    args = parser.parse_args()

    if args.command == "chat":
        return chat_command(args)

    # Se nenhum comando foi fornecido, mostra ajuda
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
