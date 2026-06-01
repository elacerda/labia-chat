# labia-chat CLI

## First Use

Install the backend package, then point the CLI at the backend and provide an
AI-Scope token:

> **Nota:** O smoke validation (`bash backend/scripts/smoke_cli.sh`) cria uma
> configuração local temporária e valida que o arquivo não contém segredos.

```bash
cd backend
python -m pip install -e ".[dev]"
export LABIA_CHAT_API_URL=http://127.0.0.1:8010
read -rsp "AI-Scope token: " LABIA_CHAT_TOKEN
export LABIA_CHAT_TOKEN
echo
```

Check the resolved configuration without printing secrets:

```bash
labia-chat --version
labia-chat config show
```

Initialize or update local non-sensitive configuration:

```bash
labia-chat config init [--api-url <url>] [--streaming-default <true|false>] [--show-last-default <n>]
```

The local config is stored at:
- `$XDG_CONFIG_HOME/labia-chat/config.toml` when `XDG_CONFIG_HOME` is set;
- otherwise `~/.config/labia-chat/config.toml`.

Persisted keys:
- `api_url` — backend URL
- `streaming_default` — enable/disable streaming by default
- `show_last_default` — number of messages to show in history

Tokens and secrets are **never** saved to the local config file.

Precedence order (highest to lowest):
CLI arguments > environment variables > local config > defaults.

Run diagnostics:

```bash
labia-chat doctor
```

Use `--with-model` only when you also want to test the existing model ping
endpoint:

```bash
labia-chat doctor --with-model
```

## Configuration

- `LABIA_CHAT_API_URL`: backend URL. Defaults to `http://127.0.0.1:8010`.
- `LABIA_CHAT_TOKEN`: AI-Scope access token. The CLI never saves this token.
- `--api-url`: overrides `LABIA_CHAT_API_URL` for one command.
- `--token`: overrides `LABIA_CHAT_TOKEN` for one command.

## Chat

Streaming is enabled by default for interactive chat and `chat send`.

```bash
labia-chat
labia-chat chat
labia-chat chat send <conversation-id> "Hello"
```

### Interactive chat

Start a new terminal chat session:

```bash
labia-chat
```

The `labia-chat` command with no arguments opens the same interactive REPL as `labia-chat chat`.

To resume an existing conversation:

```bash
labia-chat --conversation-id <conversation-id>
```

Or use the explicit form:

```bash
labia-chat chat --conversation-id <conversation-id>
```

Inside the chat:

- `/help`: show internal chat commands.
- `/history`: show recent messages for the current conversation.
- `/new`: create a new conversation and switch to it.
- `/exit` or `/quit`: leave the chat cleanly.

### Resume da conversa mais recente

Para retomar sua conversa mais recente:

```bash
labia-chat --last
labia-chat --resume-last
labia-chat chat --last
labia-chat chat --resume-last
```

Se não houver conversas anteriores, uma nova conversa será criada automaticamente.

Para retomar uma conversa específica pelo ID:

```bash
labia-chat --conversation-id <id> --show-last 5
```

Use `--no-stream` to call the non-streaming endpoint:

```bash
labia-chat chat --no-stream
labia-chat chat send <conversation-id> "Hello" --no-stream
```
