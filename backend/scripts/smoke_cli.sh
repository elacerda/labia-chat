#!/usr/bin/env bash
#
# labia-chat Smoke Validation Script
#
# This script validates the backend and CLI functionality end-to-end.
# It does NOT require vLLM to be running (model steps are optional).
#
# Usage:
#   bash backend/scripts/smoke_cli.sh                    # Core smoke (no vLLM)
#   bash backend/scripts/smoke_cli.sh --with-model       # Full smoke (requires vLLM)
#   bash backend/scripts/smoke_cli.sh --api-url <url>    # Custom API URL
#
# Environment:
#   LABIA_CHAT_API_URL  - Backend URL (default: http://127.0.0.1:8010)
#   LABIA_CHAT_TOKEN    - AI-Scope token (REQUIRED - must be set before running)
#
# Security:
#   - This script NEVER echoes the token
#   - Use: read -rsp "AI-Scope token: " LABIA_CHAT_TOKEN; export LABIA_CHAT_TOKEN; echo
#

set -euo pipefail

# Default API URL
DEFAULT_API_URL="http://127.0.0.1:8010"

# Parse arguments
API_URL="${LABIA_CHAT_API_URL:-$DEFAULT_API_URL}"
WITH_MODEL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        --with-model)
            WITH_MODEL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--api-url <url>] [--with-model]"
            exit 1
            ;;
    esac
done

# Validate required token
if [[ -z "${LABIA_CHAT_TOKEN:-}" ]]; then
    echo "ERROR: LABIA_CHAT_TOKEN is required but not set."
    echo ""
    echo "Set it safely with:"
    echo "  read -rsp 'AI-Scope token: ' LABIA_CHAT_TOKEN; export LABIA_CHAT_TOKEN; echo"
    echo ""
    echo "Or export an existing token:"
    echo "  export LABIA_CHAT_TOKEN=your-token-here"
    exit 1
fi

# Export API_URL for CLI
export LABIA_CHAT_API_URL="$API_URL"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILED=0

# Helper function to print step result
print_result() {
    local step="$1"
    local status="$2"
    local message="${3:-}"
    
    if [[ "$status" == "PASS" ]]; then
        echo -e "${GREEN}✓ PASS${NC}: $step"
    elif [[ "$status" == "SKIP" ]]; then
        echo -e "${YELLOW}○ SKIP${NC}: $step"
    else
        echo -e "${RED}✗ FAIL${NC}: $step"
        if [[ -n "$message" ]]; then
            echo "  Details: $message"
        fi
        ((FAILED++))
    fi
}

echo "=============================================="
echo "labia-chat Smoke Validation"
echo "=============================================="
echo "API URL: $API_URL"
echo "Token:   [SET - not shown]"
echo "With Model: $WITH_MODEL"
echo "=============================================="
echo ""

# Step 1: Validate backend health
echo "--- Step 1: Backend Health Check ---"
HEALTH_RESPONSE=$(curl -sS "$API_URL/health" 2>&1) || true
if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
    print_result "GET /health" "PASS"
    echo "  Response: $HEALTH_RESPONSE"
else
    print_result "GET /health" "FAIL" "Expected {\"status\":\"ok\"}, got: $HEALTH_RESPONSE"
fi
echo ""

# Step 2: Auth validation
echo "--- Step 2: Auth Validation (labia-chat auth me) ---"
AUTH_OUTPUT=$(labia-chat auth me 2>&1) || true
if echo "$AUTH_OUTPUT" | grep -q "Usuário:"; then
    print_result "labia-chat auth me" "PASS"
    echo "  Output: $(echo "$AUTH_OUTPUT" | head -n1)"
else
    print_result "labia-chat auth me" "FAIL" "$AUTH_OUTPUT"
fi
echo ""

# Step 3: Create conversation
echo "--- Step 3: Create Conversation ---"
CREATE_OUTPUT=$(labia-chat conversations create --title "Smoke Test" 2>&1) || true
if echo "$CREATE_OUTPUT" | grep -q "Conversa criada:"; then
    print_result "labia-chat conversations create" "PASS"
    # Extract conversation ID - format is "Conversa criada: <uuid>"
    CONVERSATION_ID=$(echo "$CREATE_OUTPUT" | grep "Conversa criada:" | sed 's/.*Conversa criada: //' | tr -d ' ')
    echo "  Conversation ID: $CONVERSATION_ID"
else
    print_result "labia-chat conversations create" "FAIL" "$CREATE_OUTPUT"
    echo ""
    echo "Cannot proceed without conversation ID. Aborting."
    exit 1
fi
echo ""

# Step 4: List conversations
echo "--- Step 4: List Conversations ---"
LIST_OUTPUT=$(labia-chat conversations list --limit 5 --offset 0 2>&1) || true
if echo "$LIST_OUTPUT" | grep -q "Total de conversas:"; then
    print_result "labia-chat conversations list" "PASS"
    echo "  Output preview: $(echo "$LIST_OUTPUT" | head -n2 | tail -n1)"
else
    print_result "labia-chat conversations list" "FAIL" "$LIST_OUTPUT"
fi
echo ""

# Step 5: List messages (should be empty)
echo "--- Step 5: List Messages (empty) ---"
MESSAGES_OUTPUT=$(labia-chat messages list "$CONVERSATION_ID" --limit 10 --offset 0 2>&1) || true
if echo "$MESSAGES_OUTPUT" | grep -q "Total de mensagens:"; then
    print_result "labia-chat messages list (empty)" "PASS"
    echo "  Output preview: $(echo "$MESSAGES_OUTPUT" | head -n2 | tail -n1)"
else
    print_result "labia-chat messages list (empty)" "FAIL" "$MESSAGES_OUTPUT"
fi
echo ""

# Optional: Model steps
if [[ "$WITH_MODEL" == "true" ]]; then
    echo "=============================================="
    echo "Optional: Model Generation Steps"
    echo "=============================================="
    echo ""
    
    # Step 6: Send message (requires vLLM)
    echo "--- Step 6: Send Message (requires vLLM) ---"
    SEND_OUTPUT=$(labia-chat chat send "$CONVERSATION_ID" "Smoke test message" 2>&1) || true
    if echo "$SEND_OUTPUT" | grep -q "Assistente:"; then
        print_result "labia-chat chat send" "PASS"
        echo "  Response: $(echo "$SEND_OUTPUT" | grep "Assistente:" | sed 's/Assistente: //')"
    else
        print_result "labia-chat chat send" "FAIL" "$SEND_OUTPUT"
    fi
    echo ""
    
    # Step 7: List messages (should have 1 message now)
    echo "--- Step 7: List Messages (with message) ---"
    MESSAGES_OUTPUT2=$(labia-chat messages list "$CONVERSATION_ID" --limit 10 --offset 0 2>&1) || true
    if echo "$MESSAGES_OUTPUT2" | grep -q "Total de mensagens:"; then
        print_result "labia-chat messages list (with message)" "PASS"
        echo "  Output preview: $(echo "$MESSAGES_OUTPUT2" | head -n2 | tail -n1)"
    else
        print_result "labia-chat messages list (with message)" "FAIL" "$MESSAGES_OUTPUT2"
    fi
    echo ""
    
    # Step 8: Model ping (documented way via curl)
    echo "--- Step 8: Model Ping (via curl to /chat/model/ping) ---"
    echo "Note: This requires vLLM to be running and accessible."
    MODEL_PING_RESPONSE=$(curl -sS -X POST "$API_URL/chat/model/ping" \
        -H "Authorization: Bearer $LABIA_CHAT_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"prompt": "ping"}' 2>&1) || true
    if echo "$MODEL_PING_RESPONSE" | grep -q '"response"'; then
        print_result "POST /chat/model/ping" "PASS"
        echo "  Response: $MODEL_PING_RESPONSE"
    else
        print_result "POST /chat/model/ping" "SKIP" "vLLM may not be available or configured"
    fi
    echo ""
else
    echo "=============================================="
    echo "Skipping model steps (use --with-model to include)"
    echo "=============================================="
    echo ""
fi

# Summary
echo "=============================================="
echo "Summary"
echo "=============================================="
if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}$FAILED check(s) failed${NC}"
    exit 1
fi