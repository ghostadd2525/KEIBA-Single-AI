# Version 5 — Conversation Health Check

## Endpoint

`GET /v1/conversation/health`（Observability 拡張）

Envelope:

```json
{
  "ok": true,
  "data": {
    "status": "ok|degraded",
    "overall_ok": true,
    "components": {
      "conversation_api": {"ok": true},
      "ollama": {"ok": true, "reachable": true, "models": ["qwen2.5:1.5b"]},
      "knowledge_runtime": {"ok": true, "search_latency_ms": 1.2, "hit_count": 0, "top_k": 5},
      "tool_manager": {"ok": true, "enabled": true},
      "prediction_connector": {"ok": true, "read_only": true}
    },
    "platform_health": { "...": "v4 health() unchanged payload embedded" },
    "metrics": { "...": "snapshot" }
  },
  "meta": {"service": "ConversationObservability", "platform": "v4"}
}
```

## Checks

| Component | How |
|-----------|-----|
| Conversation API | process answers health |
| Ollama | existing v4 health ollama reachability (flag ON) |
| Knowledge Runtime | read-only `KnowledgeProvider.search` probe |
| Tool Manager | `F_V4_TOOL_LAYER` surface |
| Prediction Connector | connector import + optional health / platform flags |

## BFF probe

`conversation_health` in `functions/_lib/opsMonitor.js` → Alert **ALT-C04** on NG.
