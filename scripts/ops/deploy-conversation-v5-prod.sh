#!/usr/bin/env bash
# Production Deploy — Conversation Version 5
# Usage: sudo bash scripts/ops/deploy-conversation-v5-prod.sh [--skip-git] [--skip-ollama] [--model NAME] [--verify-only]
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/ubuntu/KEIBA-Single-AI}"
SERVICE_UNIT="/etc/systemd/system/expect-ai.service"
ENV_DST="/etc/expect-ai/conversation.env"
SKIP_GIT=0
SKIP_OLLAMA=0
VERIFY_ONLY=0
MODEL_OVERRIDE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-git) SKIP_GIT=1 ;;
    --skip-ollama) SKIP_OLLAMA=1 ;;
    --verify-only) VERIFY_ONLY=1 ;;
    --model) MODEL_OVERRIDE="${2:-}"; shift ;;
    -h|--help) echo "see docs/releases/v5-production-deployment-report.md"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

log() { printf '[deploy-v5] %s\n' "$*"; }
die() { printf '[deploy-v5] ERROR: %s\n' "$*" >&2; exit 1; }

verify_smoke() {
  log "health"
  curl -sf --max-time 5 http://127.0.0.1:8000/health | head -c 240 || true
  echo
  log "conversation health"
  curl -sf --max-time 8 http://127.0.0.1:8000/v1/conversation/health | head -c 500 \
    || die "conversation health failed"
  echo
  log "personal chat smoke"
  local body
  body="$(curl -sf --max-time 60 -X POST http://127.0.0.1:8000/v1/conversation/chat \
    -H 'Content-Type: application/json' \
    -d '{"message":"hello","mode":"chat","context":{"type":"personal_chat","mode":"chat"}}')"
  printf '%s\n' "$body" | head -c 900
  echo
  export CHAT_BODY="$body"
  python3 - <<'PY'
import json, os, sys
d = json.loads(os.environ.get("CHAT_BODY") or "")
data = d.get("data") or d
meta = d.get("meta") or {}
agent = data.get("agent")
orch = bool(data.get("orchestrator"))
llm = data.get("llm") or {}
platform = meta.get("platform") or data.get("platform")
service = str(meta.get("service") or "")
print("--- parse ---")
print("agent=", agent)
print("orchestrator=", orch)
print("platform=", platform)
print("service=", service)
print("ollama_called=", llm.get("ollama_called"))
print("llm.used=", llm.get("used"))
ok = agent == "chat" and (orch or platform == "v4" or service.endswith("Orchestrator"))
if not ok:
    sys.exit("FAIL: Conversation V5/V4 orchestrator path not active")
if llm.get("ollama_called") is not True:
    sys.exit("FAIL: llm.ollama_called is not true")
print("PASS")
PY
}

if [[ "$VERIFY_ONLY" -eq 1 ]]; then
  verify_smoke
  exit 0
fi

[[ "${EUID}" -eq 0 ]] || die "run with sudo"
[[ -d "$REPO_ROOT" ]] || die "repo not found: $REPO_ROOT"
cd "$REPO_ROOT"

if [[ "$SKIP_GIT" -eq 0 ]]; then
  log "git fetch/pull"
  [[ -d .git ]] || die "not a git checkout"
  sudo -u ubuntu git fetch origin
  sudo -u ubuntu git checkout main
  sudo -u ubuntu git pull --ff-only origin main || die "git pull failed"
fi

[[ -d services/win5-ai/app/conversation/v4 ]] || die "missing conversation/v4"
[[ -d services/win5-ai/app/conversation/v5 ]] || die "missing conversation/v5"

ENV_SRC=""
for c in \
  "${REPO_ROOT}/services/win5-ai/config/production/conversation.env" \
  "${REPO_ROOT}/infra/aws/systemd/conversation.env.example"
do
  if [[ -f "$c" ]]; then ENV_SRC="$c"; break; fi
done
[[ -n "$ENV_SRC" ]] || die "conversation.env source missing"

log "install $ENV_DST from $ENV_SRC"
mkdir -p /etc/expect-ai
cp -f "$ENV_SRC" "$ENV_DST"
if [[ -n "$MODEL_OVERRIDE" ]]; then
  if grep -q '^CONVERSATION_DEFAULT_MODEL=' "$ENV_DST"; then
    sed -i "s|^CONVERSATION_DEFAULT_MODEL=.*|CONVERSATION_DEFAULT_MODEL=${MODEL_OVERRIDE}|" "$ENV_DST"
  else
    echo "CONVERSATION_DEFAULT_MODEL=${MODEL_OVERRIDE}" >>"$ENV_DST"
  fi
fi
chmod 640 "$ENV_DST"
chown root:ubuntu "$ENV_DST" 2>/dev/null || true

if [[ -f "$SERVICE_UNIT" ]] && ! grep -q 'conversation.env' "$SERVICE_UNIT"; then
  log "wire EnvironmentFile into expect-ai.service"
  python3 - "$SERVICE_UNIT" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
needle = "EnvironmentFile=-/etc/expect-ai/conversation.env"
if needle in text:
    raise SystemExit(0)
lines = text.splitlines()
out = []
inserted = False
last_env = -1
for i, line in enumerate(lines):
    if line.startswith("EnvironmentFile="):
        last_env = i
for i, line in enumerate(lines):
    out.append(line)
    if i == last_env and not inserted:
        out.append(needle)
        inserted = True
if not inserted:
    for i, line in enumerate(list(out)):
        if line.strip() == "[Service]":
            out.insert(i + 1, needle)
            inserted = True
            break
if not inserted:
    out.append(needle)
path.write_text("\n".join(out) + "\n", encoding="utf-8")
print("wired", path)
PY
  systemctl daemon-reload
fi

MODEL="$(grep -E '^CONVERSATION_DEFAULT_MODEL=' "$ENV_DST" | tail -1 | cut -d= -f2- || true)"
if [[ -n "$MODEL_OVERRIDE" ]]; then MODEL="$MODEL_OVERRIDE"; fi
if [[ -z "$MODEL" ]]; then MODEL="qwen2.5:1.5b"; fi

if [[ "$SKIP_OLLAMA" -eq 0 ]]; then
  log "ensure Ollama model=$MODEL"
  if ! command -v ollama >/dev/null 2>&1; then
    curl -fsSL https://ollama.com/install.sh | sh
  fi
  if [[ "$(swapon --show | wc -l)" -eq 0 ]]; then
    log "creating 2G swapfile"
    if [[ ! -f /swapfile ]]; then
      fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
      chmod 600 /swapfile
      mkswap /swapfile
    fi
    swapon /swapfile || true
    grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >>/etc/fstab
  fi
  systemctl enable --now ollama
  sleep 2
  curl -sf --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null \
    || die "Ollama not reachable"
  if ! ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$MODEL"; then
    log "ollama pull $MODEL"
    ollama pull "$MODEL"
  else
    log "model present: $MODEL"
  fi
fi

log "restart expect-ai"
systemctl restart expect-ai
sleep 3
systemctl is-active --quiet expect-ai || die "expect-ai failed to start"

verify_smoke
log "deploy complete"
