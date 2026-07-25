#!/usr/bin/env bash
# =============================================================================
# Production Deploy — Conversation Version 5 (Platform + Knowledge Runtime)
#
# Purpose:
#   Reflect Conversation V4/V5 onto the expect-ai EC2 host and enable flags.
#   Prediction AI / Ranking / Confidence / Purchase are NOT modified.
#
# Usage (on EC2 as ubuntu with sudo):
#   cd /home/ubuntu/KEIBA-Single-AI
#   sudo bash scripts/ops/deploy-conversation-v5-prod.sh
#
# Options:
#   --skip-git      do not git pull
#   --skip-ollama   do not install/start Ollama
#   --model NAME    Ollama model (default from conversation.env or qwen2.5:1.5b)
#   --verify-only   only run health / chat smoke (no code/env changes)
#
# Why enable-conversation-v5-prod.sh was missing on EC2:
#   V4/V5 packages and ops scripts lived only in a local working tree and were
#   never committed/pushed to origin/main. EC2 main stopped at Version 2.
# =============================================================================
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/ubuntu/KEIBA-Single-AI}"
SERVICE_UNIT="/etc/systemd/system/expect-ai.service"
ENV_DST="/etc/expect-ai/conversation.env"
ENV_SRC_CANDIDATES=(
  "${REPO_ROOT}/services/win5-ai/config/production/conversation.env"
  "${REPO_ROOT}/infra/aws/systemd/conversation.env.example"
)
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
    -h|--help)
      sed -n '2,30p' "$0"
      exit 0
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 2
      ;;
  esac
  shift
done

log() { printf '[deploy-v5] %s\n' "$*"; }
die() { printf '[deploy-v5] ERROR: %s\n' "$*" >&2; exit 1; }

need_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    die "run with sudo"
  fi
}

verify_smoke() {
  log "health"
  curl -sf --max-time 5 http://127.0.0.1:8000/health | head -c 240 || true
  echo
  log "conversation health"
  curl -sf --max-time 8 http://127.0.0.1:8000/v1/conversation/health | head -c 500 \
    || die "conversation health failed — V4/V5 code or flags missing"
  echo
  log "personal chat smoke"
  local body
  body="$(curl -sf --max-time 45 -X POST http://127.0.0.1:8000/v1/conversation/chat \
    -H 'Content-Type: application/json' \
    -d '{"message":"今日の気分は？","mode":"chat","context":{"type":"personal_chat","mode":"chat"}}")"
  printf '%s\n' "$body" | head -c 900
  echo
  CHAT_BODY="$body" python3 - <<'PY'
import json, os, sys
raw = os.environ.get("CHAT_BODY") or ""
d = json.loads(raw)
data = d.get("data") or d
meta = d.get("meta") or {}
agent = data.get("agent")
orch = bool(data.get("orchestrator"))
llm = data.get("llm") or {}
platform = meta.get("platform") or data.get("platform")
print("--- parse ---")
print("agent=", agent)
print("orchestrator=", orch)
print("platform=", platform)
print("service=", meta.get("service"))
print("ollama_called=", llm.get("ollama_called"))
print("llm.used=", llm.get("used"))
ok = agent == "chat" and (orch or platform == "v4" or str(meta.get("service", "")).endswith("Orchestrator"))
if not ok:
    raise SystemExit("FAIL: Conversation V5/V4 orchestrator path not active")
if llm.get("ollama_called") is not True:
    raise SystemExit("FAIL: llm.ollama_called is not true")
print("PASS")
PY
}

if [[ "$VERIFY_ONLY" -eq 1 ]]; then
  verify_smoke
  exit 0
fi

need_root

[[ -d "$REPO_ROOT" ]] || die "repo not found: $REPO_ROOT"
cd "$REPO_ROOT"

if [[ "$SKIP_GIT" -eq 0 ]]; then
  log "git fetch/pull (preserve local PI/collector dirty files)"
  if [[ -d .git ]]; then
    sudo -u ubuntu git fetch origin
    # Prefer origin/main tip; keep local modifications outside conversation if any
    sudo -u ubuntu git checkout main
    sudo -u ubuntu git pull --ff-only origin main || {
      log "ff-only failed — attempting conversation-path checkout from origin/main"
      sudo -u ubuntu git checkout origin/main -- \
        services/win5-ai/app/conversation \
        services/win5-ai/app/main.py \
        services/win5-ai/config/production/conversation.env \
        infra/aws/systemd/conversation.env.example \
        infra/aws/systemd/expect-ai.service.example \
        scripts/ops/deploy-conversation-v5-prod.sh \
        scripts/ops/enable-conversation-v5-prod.sh \
        || die "could not sync conversation paths from origin/main"
    }
  else
    die "not a git checkout; sync code first"
  fi
fi

[[ -d services/win5-ai/app/conversation/v4 ]] || die "missing conversation/v4 after sync"
[[ -d services/win5-ai/app/conversation/v5 ]] || die "missing conversation/v5 after sync"

ENV_SRC=""
for c in "${ENV_SRC_CANDIDATES[@]}"; do
  if [[ -f "$c" ]]; then ENV_SRC="$c"; break; fi
done
[[ -n "$ENV_SRC" ]] || die "conversation.env source missing"

log "install $ENV_DST from $ENV_SRC"
mkdir -p /etc/expect-ai
cp -f "$ENV_SRC" "$ENV_DST"
# EC2 t3.small (~2GiB): prefer small chat model unless operator overrides
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
  python3 - <<'PY' "$SERVICE_UNIT"
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
MODEL="${MODEL_OVERRIDE:-${MODEL:-qwen2.5:1.5b}}"

if [[ "$SKIP_OLLAMA" -eq 0 ]]; then
  log "ensure Ollama (model=$MODEL)"
  if ! command -v ollama >/dev/null 2>&1; then
    curl -fsSL https://ollama.com/install.sh | sh
  fi
  # Small instance safety: add swap if none
  if [[ "$(swapon --show | wc -l)" -eq 0 ]]; then
    log "creating 2G swapfile for LLM headroom"
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
    || die "Ollama not reachable on 127.0.0.1:11434"
  # Pull only if missing
  if ! ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$MODEL"; then
    log "ollama pull $MODEL"
    ollama pull "$MODEL"
  else
    log "model already present: $MODEL"
  fi
fi

log "restart expect-ai"
systemctl restart expect-ai
sleep 3
systemctl is-active --quiet expect-ai || die "expect-ai failed to start"

verify_smoke
log "deploy complete"
