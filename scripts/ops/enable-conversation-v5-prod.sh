#!/usr/bin/env bash
# Compatibility wrapper — prefer deploy-conversation-v5-prod.sh for full reflection.
# Historical note: this file was missing on EC2 because V5 ops scripts were never
# pushed to origin/main (local-only working tree).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec bash "$ROOT/scripts/ops/deploy-conversation-v5-prod.sh" "$@"
