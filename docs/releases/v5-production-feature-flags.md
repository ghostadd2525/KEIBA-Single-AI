# Version 5 — Production Feature Flags

**Parent:** [`v5-production-rollout-report.md`](./v5-production-rollout-report.md)  
**Config file:** `services/win5-ai/config/production/conversation.env`

| Flag | Production | Default (code) | Notes |
|------|------------|----------------|-------|
| `F_V4_CONVERSATION_ENABLED` | ON | OFF | Platform master |
| `F_V4_REVIEW_AGENT` | ON | OFF | Review |
| `F_V4_PERSONAL_CHAT` | ON | OFF | Personal Chat（Guard は別途常時） |
| `F_V4_TOOL_LAYER` | ON | OFF | Canonical Tool Manager |
| `F_V4_KNOWLEDGE_LAYER` | ON | OFF | Knowledge Tool |
| `F_V5_KNOWLEDGE_RUNTIME` | ON | OFF | RAG Runtime |
| `F_V4_KNOWLEDGE_INTEGRATION` | OFF | OFF | External vector 未接続 |
| `F_V4_CONVERSATION_OLLAMA` | OFF | OFF | LLM optional |

Security Guard / Prediction Read Only: **Flag で OFF 不可**（ADR-001 / ADR-003）。
