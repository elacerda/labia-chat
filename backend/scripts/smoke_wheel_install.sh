#!/usr/bin/env bash
#
# Build and install smoke validation for the labia-chat CLI wheel.
#
# Usage:
#   bash backend/scripts/smoke_wheel_install.sh
#   bash backend/scripts/smoke_wheel_install.sh --api-url http://orion.cbpf.br:8010
#   bash backend/scripts/smoke_wheel_install.sh --with-backend
#   bash backend/scripts/smoke_wheel_install.sh --interactive-login
#   bash backend/scripts/smoke_wheel_install.sh --keep
#
# This script does not require or print AI-Scope credentials by default.

set -euo pipefail

DEFAULT_API_URL="http://orion.cbpf.br:8010"
API_URL="$DEFAULT_API_URL"
WITH_BACKEND=false
INTERACTIVE_LOGIN=false
KEEP=false
FAILED=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
    cat <<EOF
Usage: $0 [--api-url URL] [--with-backend] [--interactive-login] [--keep]

Options:
  --api-url URL          Backend URL to write into CLI config.
                         Default: $DEFAULT_API_URL
  --with-backend         Require GET /health to pass for the configured backend.
  --interactive-login    Manually exercise the real AI-Scope login flow.
  --keep                 Keep temporary venv, config, and wheel artifacts.
  -h, --help             Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --api-url)
            if [[ $# -lt 2 || "$2" == --* ]]; then
                echo "FAIL: --api-url requires a URL" >&2
                exit 2
            fi
            API_URL="$2"
            shift 2
            ;;
        --with-backend)
            WITH_BACKEND=true
            shift
            ;;
        --interactive-login)
            INTERACTIVE_LOGIN=true
            shift
            ;;
        --keep)
            KEEP=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "FAIL: unknown option: $1" >&2
            usage
            exit 2
            ;;
    esac
done

pass() {
    echo "PASS: $1"
}

skip() {
    echo "SKIP: $1"
}

fail() {
    local step="$1"
    local detail="${2:-}"

    echo "FAIL: $step" >&2
    if [[ -n "$detail" ]]; then
        echo "      $detail" >&2
    fi
    FAILED=$((FAILED + 1))
}

run_step() {
    local step="$1"
    shift

    if "$@"; then
        pass "$step"
    else
        fail "$step"
    fi
}

critical_step() {
    local step="$1"
    shift

    if "$@"; then
        pass "$step"
    else
        fail "$step"
        echo "RESULT: FAIL (cannot continue after: $step)" >&2
        exit 1
    fi
}

contains() {
    local needle="$1"
    local haystack="$2"
    grep -Fq "$needle" <<<"$haystack"
}

health_check() {
    python - "$API_URL" <<'PY'
import json
import sys
import urllib.error
import urllib.request

api_url = sys.argv[1].rstrip("/")
try:
    with urllib.request.urlopen(f"{api_url}/health", timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
except (OSError, urllib.error.URLError, json.JSONDecodeError):
    raise SystemExit(1)

raise SystemExit(0 if payload.get("status") == "ok" else 1)
PY
}

echo "=============================================="
echo "labia-chat wheel install smoke validation"
echo "=============================================="
echo "Backend dir: $BACKEND_DIR"
echo "API URL:     $API_URL"
echo "Backend:     $([[ "$WITH_BACKEND" == true ]] && echo required || echo optional)"
echo "Login:       $([[ "$INTERACTIVE_LOGIN" == true ]] && echo manual || echo skipped)"
echo "=============================================="
echo

cd "$BACKEND_DIR"

TMP_ROOT="$(mktemp -d)"
VENV_DIR="$TMP_ROOT/venv"
WHEEL_DIR="$TMP_ROOT/wheelhouse"
XDG_DIR="$TMP_ROOT/xdg-config"

cleanup() {
    if [[ "$KEEP" == true ]]; then
        echo
        echo "Keeping temporary artifacts:"
        echo "  $TMP_ROOT"
        return
    fi
    rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

mkdir -p "$WHEEL_DIR" "$XDG_DIR"

export XDG_CONFIG_HOME="$XDG_DIR"
unset LABIA_CHAT_TOKEN
unset LABIA_CHAT_API_URL

critical_step "create clean virtual environment" python -m venv "$VENV_DIR"

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
    echo "RESULT: FAIL (virtual environment was not created)" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

critical_step "upgrade installer tools" python -m pip install --upgrade pip setuptools wheel

critical_step "build wheel from backend" python -m pip wheel --no-deps --wheel-dir "$WHEEL_DIR" "$BACKEND_DIR"

WHEEL_PATH="$(find "$WHEEL_DIR" -maxdepth 1 -type f -name 'labia_chat-*.whl' | sort | tail -n 1)"
if [[ -n "$WHEEL_PATH" && -f "$WHEEL_PATH" ]]; then
    pass "locate built wheel ($(basename "$WHEEL_PATH"))"
else
    fail "locate built wheel" "No labia_chat wheel found in $WHEEL_DIR"
    echo "RESULT: FAIL (cannot continue without a wheel)" >&2
    exit 1
fi

critical_step "install wheel into clean virtual environment" python -m pip install "$WHEEL_PATH"

VERSION_OUTPUT="$(labia-chat --version 2>&1)" || {
    fail "labia-chat --version" "$VERSION_OUTPUT"
    VERSION_OUTPUT=""
}
if contains "labia-chat" "$VERSION_OUTPUT"; then
    pass "labia-chat --version"
else
    fail "labia-chat --version output" "$VERSION_OUTPUT"
fi

HELP_OUTPUT="$(labia-chat --help 2>&1)" || {
    fail "labia-chat --help" "$HELP_OUTPUT"
    HELP_OUTPUT=""
}
if contains "CLI para chat" "$HELP_OUTPUT"; then
    pass "labia-chat --help"
else
    fail "labia-chat --help output" "$HELP_OUTPUT"
fi

CONFIG_INIT_OUTPUT="$(labia-chat config init --api-url "$API_URL" --streaming-default true --show-last-default 5 2>&1)" || {
    fail "labia-chat config init" "$CONFIG_INIT_OUTPUT"
    CONFIG_INIT_OUTPUT=""
}
if contains "Configuração salva com sucesso." "$CONFIG_INIT_OUTPUT"; then
    pass "labia-chat config init"
else
    fail "labia-chat config init output" "$CONFIG_INIT_OUTPUT"
fi

CONFIG_FILE="$XDG_CONFIG_HOME/labia-chat/config.toml"
if [[ -f "$CONFIG_FILE" ]]; then
    pass "isolated XDG config file created"
else
    fail "isolated XDG config file created" "Missing $CONFIG_FILE"
fi

if [[ -f "$CONFIG_FILE" ]] && ! grep -Eiq 'token|password|authorization|bearer|secret' "$CONFIG_FILE"; then
    pass "config file contains no token/password fields"
else
    fail "config file contains no token/password fields" "$CONFIG_FILE"
fi

CONFIG_SHOW_OUTPUT="$(labia-chat config show 2>&1)" || {
    fail "labia-chat config show" "$CONFIG_SHOW_OUTPUT"
    CONFIG_SHOW_OUTPUT=""
}
if contains "URL da API: $API_URL" "$CONFIG_SHOW_OUTPUT" \
    && contains "Origem da URL da API: config" "$CONFIG_SHOW_OUTPUT" \
    && contains "Status do token: ausente" "$CONFIG_SHOW_OUTPUT"; then
    pass "labia-chat config show"
else
    fail "labia-chat config show output" "$CONFIG_SHOW_OUTPUT"
fi

AUTH_MISSING_OUTPUT="$(labia-chat auth me --api-url "$API_URL" 2>&1 </dev/null)" && AUTH_MISSING_STATUS=0 || AUTH_MISSING_STATUS=$?
if [[ "$AUTH_MISSING_STATUS" -ne 0 ]] \
    && contains "token AI-Scope ausente" "$AUTH_MISSING_OUTPUT" \
    && ! contains "AI-Scope username:" "$AUTH_MISSING_OUTPUT" \
    && ! contains "AI-Scope password:" "$AUTH_MISSING_OUTPUT"; then
    pass "non-interactive auth me does not prompt without token"
else
    fail "non-interactive auth me does not prompt without token" "$AUTH_MISSING_OUTPUT"
fi

LIST_MISSING_OUTPUT="$(labia-chat conversations list --api-url "$API_URL" 2>&1 </dev/null)" && LIST_MISSING_STATUS=0 || LIST_MISSING_STATUS=$?
if [[ "$LIST_MISSING_STATUS" -ne 0 ]] \
    && contains "token AI-Scope ausente" "$LIST_MISSING_OUTPUT" \
    && ! contains "AI-Scope username:" "$LIST_MISSING_OUTPUT" \
    && ! contains "AI-Scope password:" "$LIST_MISSING_OUTPUT"; then
    pass "non-interactive conversations list does not prompt without token"
else
    fail "non-interactive conversations list does not prompt without token" "$LIST_MISSING_OUTPUT"
fi

if health_check; then
    pass "GET /health at $API_URL"
elif [[ "$WITH_BACKEND" == true ]]; then
    fail "GET /health at $API_URL" "Backend is required by --with-backend"
else
    skip "GET /health at $API_URL (backend unavailable)"
fi

if [[ "$INTERACTIVE_LOGIN" == true ]]; then
    echo
    echo "Manual interactive login check."
    echo "Credentials are read by labia-chat and are not printed by this script."
    echo "Exit the chat with /exit after login succeeds."
    if labia-chat chat --api-url "$API_URL" --show-last 0; then
        pass "manual interactive login flow"
    else
        fail "manual interactive login flow"
    fi
else
    skip "manual interactive AI-Scope login flow"
fi

echo
if [[ "$FAILED" -eq 0 ]]; then
    echo "RESULT: PASS"
    exit 0
fi

echo "RESULT: FAIL ($FAILED failure(s))"
exit 1
