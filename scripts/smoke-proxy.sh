#!/usr/bin/env bash
set -euo pipefail

FRONTEND_URL="${FRONTEND_URL:-http://localhost:3060}"
PROXY_HEALTH_URL="${PROXY_HEALTH_URL:-http://localhost:3060/api/v1/health}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://localhost:8060/api/v1/health}"

_pass() { echo "PASS: $*"; }
_fail() { echo "FAIL: $*" >&2; exit 1; }
_warn() { echo "WARN: $*" >&2; }

_curl_ok() {
  local url="$1"
  # Fail fast; no retries; no output to stdout.
  curl -fsS --max-time 5 --connect-timeout 2 "$url" >/dev/null
}

echo "Smoke proxy check"
echo "  frontend:      $FRONTEND_URL"
echo "  proxied health: $PROXY_HEALTH_URL"
echo "  direct health:  $BACKEND_HEALTH_URL"
echo ""

if _curl_ok "$FRONTEND_URL"; then
  _pass "frontend reachable"
else
  _fail "frontend unreachable: $FRONTEND_URL"
fi

if _curl_ok "$PROXY_HEALTH_URL"; then
  _pass "proxied backend health reachable via frontend (/api)"
else
  _fail "proxied backend health unreachable via frontend: $PROXY_HEALTH_URL"
fi

if _curl_ok "$BACKEND_HEALTH_URL"; then
  _pass "direct backend health reachable (ops/debug)"
else
  _warn "direct backend health unreachable (ok if locked down): $BACKEND_HEALTH_URL"
fi

_pass "smoke-proxy complete"

