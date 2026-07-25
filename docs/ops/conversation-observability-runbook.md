# Conversation Observability Runbook

Parent: [`docs/releases/v5-observability-report.md`](../releases/v5-observability-report.md)

## Quick checks

```bash
curl -sf http://127.0.0.1:8000/v1/conversation/health | jq .
curl -sf http://127.0.0.1:8000/v1/ops/conversation/metrics | jq .
curl -sf http://127.0.0.1:8000/v1/ops/conversation/dashboard | jq '.data.categories,.data.alerts'
```

Pages: open `ops.html` → **Conversation Metrics**.

---

## ALT-C01 — Ollama timeout

1. `curl -sf http://127.0.0.1:11434/api/tags`
2. `systemctl status ollama expect-ai`
3. Check model: `/etc/expect-ai/conversation.env` → `CONVERSATION_DEFAULT_MODEL`
4. On t3.small prefer `qwen2.5:1.5b`; raise timeout `CONVERSATION_OLLAMA_TIMEOUT_MS`

## ALT-C02 — Conversation error rate

1. Inspect recent JSONL: `tail -n 50 /home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/ops/conversation_metrics.jsonl`
2. Hit Personal Chat smoke and inspect `fallback` / `error_reason`
3. Confirm flags ON in `/v1/conversation/health`
4. If Legacy path: re-run `scripts/ops/deploy-conversation-v5-prod.sh --verify-only`

## ALT-C03 — Knowledge Runtime failure

1. Confirm `F_V5_KNOWLEDGE_RUNTIME=ON` / `F_V4_KNOWLEDGE_LAYER=ON`
2. Re-run health; inspect `components.knowledge_runtime.error`
3. Do **not** change Knowledge Runtime internals under Freeze — ops restart only:
   `sudo systemctl restart expect-ai`

## ALT-C04 — Health check NG

1. List failed components from health payload
2. Ollama NG → ALT-C01 steps
3. Tool Manager NG → ensure `F_V4_TOOL_LAYER=ON` in conversation.env
4. Prediction connector NG → check Prediction API separately（Conversation は Read Only）

## Rollback observability only

Observability is additive. To disable recording without Platform rollback, restart is enough after removing routes is **not** required for Freeze. Temporary: ignore `/api/ops/conversation` in ops UI.
