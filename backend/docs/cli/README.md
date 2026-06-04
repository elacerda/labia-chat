# labia-chat CLI Distribution

This document covers local wheel validation and internal distribution checks for
the backend package that provides the `labia-chat` command.

The primary repository is the internal GitLab repository. The GitHub repository
is a mirror for convenience.

## Build and Install from a Wheel

From the repository root:

```bash
cd backend
python -m pip install --upgrade pip setuptools wheel
python -m pip wheel --no-deps --wheel-dir dist .
python -m venv /tmp/labia-chat-wheel-test
/tmp/labia-chat-wheel-test/bin/python -m pip install dist/labia_chat-*.whl
/tmp/labia-chat-wheel-test/bin/labia-chat --version
/tmp/labia-chat-wheel-test/bin/labia-chat --help
```

For a normal developer install, editable mode is still useful:

```bash
cd backend
python -m pip install -e ".[dev]"
```

This patch does not implement PyPI publishing.

## Smoke Wheel Install Script

Run the reproducible wheel/install validation from the repository root:

```bash
bash backend/scripts/smoke_wheel_install.sh
```

The script builds a wheel from `backend/`, creates a clean temporary virtual
environment, installs the wheel, and runs:

- `labia-chat --version`
- `labia-chat --help`
- `labia-chat config init`
- `labia-chat config show`
- non-interactive auth/list commands with no token, confirming they fail without
  prompting for AI-Scope login

The script uses an isolated temporary `XDG_CONFIG_HOME`, does not require
`LABIA_CHAT_TOKEN` by default, and does not print or ask for AI-Scope passwords
or tokens by default.

Useful options:

```bash
bash backend/scripts/smoke_wheel_install.sh --api-url http://127.0.0.1:8010
bash backend/scripts/smoke_wheel_install.sh --with-backend --api-url http://127.0.0.1:8010
bash backend/scripts/smoke_wheel_install.sh --interactive-login
bash backend/scripts/smoke_wheel_install.sh --keep
```

`--with-backend` requires `GET /health` to pass. Without it, backend health is
checked when available and skipped when unavailable. `--keep` leaves the
temporary virtual environment, wheelhouse, and config directory on disk for
inspection.

## Backend URL

The CLI defaults to:

```text
http://127.0.0.1:8010
```

Use `--api-url` or `LABIA_CHAT_API_URL` to point at a different backend. The
local operational Docker Compose setup can be run outside this repository at:

```bash
cd ~/services/labia-chat
docker compose up
```

That external setup is expected to expose the backend at
`http://127.0.0.1:8010`. Do not commit that compose setup into this repository.

## Auth and Secrets

Interactive chat entrypoints can prompt for AI-Scope username and password when
no token is provided:

```bash
labia-chat
labia-chat chat
labia-chat --last
labia-chat chat --resume-last
```

The token returned by interactive login is kept only in memory for that process.
Tokens and passwords are not saved in `config.toml`.

Non-interactive commands do not prompt for login. They require `--token` or
`LABIA_CHAT_TOKEN`:

```bash
export LABIA_CHAT_TOKEN=<ai-scope-token>
labia-chat auth me
labia-chat conversations list
labia-chat chat send <conversation-id> "Hello"
```

Or for a single command:

```bash
labia-chat auth me --token <ai-scope-token>
```

The backend requires a valid AI-Scope token for `/chat/*`, and the authenticated
user must be active and have the `chat_vllm` role.

Local CLI configuration stores only non-sensitive settings such as `api_url`,
`streaming_default`, and `show_last_default`.
