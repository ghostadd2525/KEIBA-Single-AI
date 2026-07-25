# Version 5 — Conversation Metrics Specification

**Schema:** `expect-conversation-observability/1.0`  
**Recorder:** `services/win5-ai/app/ops/conversation_observability.py`  
**Persistence:** `var/ops/conversation_metrics.jsonl`（API boundary 追記）

## Conversation

| Metric | Type | Source |
|--------|------|--------|
| `request_count` | counter | each `/v1/conversation/chat` |
| `success_count` | counter | non-block success replies |
| `error_count` | counter | explicit error / fail-open without orchestrated reply |
| `error_rate` | ratio | `error_count / request_count` |
| `latency_ms.p50/p95/p99` | histogram summary | rolling window (default 500) |
| `review_count` | counter | agent/mode review |
| `explain_count` | counter | agent expert / mode explain |
| `chat_count` | counter | agent/mode chat |

## Ollama

| Metric | Type | Notes |
|--------|------|-------|
| `response_time_ms.p50/p95/p99` | summary | samples where `llm.ollama_called=true` |
| `timeout_count` | counter | timeout markers in llm/fallback |
| `error_count` | counter | llm error markers |
| `tokens_input` / `tokens_output` | counter | **optional** — Platform 未公開時は 0 · `tokens_available=false` |
| `model_name` | gauge/label | last successful model |

## Knowledge Runtime

| Metric | Type | Source |
|--------|------|--------|
| `search_count` | counter | tools_used knowledge **or** health probe search |
| `search_latency_ms.*` | summary | probe + inferred |
| `retrieval_hit` / `retrieval_miss` | counter | hit_count / citations |
| `top_k` | config | `CONVERSATION_KNOWLEDGE_TOP_K` (default 5) |

## Security Guard

| Metric | Type | Source |
|--------|------|--------|
| `block_count` | counter | blocked intents / security_block |
| `allow_count` | counter | non-block requests |
| `block_reason` | map | reason → count |

## Non-goals

- Platform 内部への Counter 埋め込み
- Memory / RAG 改善 / Knowledge 内容追加
