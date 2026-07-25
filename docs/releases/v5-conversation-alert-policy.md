# Version 5 — Conversation Alert Policy

| ID | Trigger | Severity | Source |
|----|---------|----------|--------|
| ALT-C01 | `ollama.timeout_count >= CONV_ALERT_OLLAMA_TIMEOUT` (default 3) | warning | metrics |
| ALT-C02 | `request_count >= 10` and `error_rate >= CONV_ALERT_ERROR_RATE` (default 0.2) · also probe `conversation_api` fail | critical | metrics / BFF probe |
| ALT-C03 | Knowledge Runtime health component `ok=false` | warning | health probe |
| ALT-C04 | Conversation health `overall_ok=false` · probe `conversation_health` | critical | health / BFF |

## Env knobs

```bash
CONV_ALERT_ERROR_RATE=0.2
CONV_ALERT_OLLAMA_TIMEOUT=3
CONVERSATION_KNOWLEDGE_TOP_K=5
```

## Dispatch

- Evaluated in `evaluate_alerts()` and returned by dashboard/alerts APIs.
- BFF `ALERT_BY_CHECK` maps probe failures to ALT-C02 / ALT-C04 for existing Slack dispatch path.
