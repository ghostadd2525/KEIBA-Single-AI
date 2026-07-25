# Version 5 — Production Verification Result

**Date:** 2026-07-25  
**SHA:** `b0666f7`  
**Verdict:** PASS (Conversation V5 reflected · Personal Chat uses Ollama)

---

## A. Public BFF (stop condition)

`POST https://expect-keiba.com/api/conversation/chat`

```json
{
  "mode": "chat",
  "context": {"type": "personal_chat", "mode": "chat"},
  "message": "hello"
}
```

| Field | Expected | Observed |
|-------|----------|----------|
| `meta.provider` | not `python_legacy_guarded` | `python` |
| `meta.fallback` | absent / not legacy guard | `null` |
| `data.agent` | `chat` | `chat` |
| `data.orchestrator` | `true` | `true` |
| `data.llm.ollama_called` | `true` | `true` |
| `data.llm.used` | `true` | `true` |

**PASS** — no longer stuck on Legacy race-required guard.

---

## B. EC2 local Orchestrator smoke

| Mode | agent | orchestrator | notes |
|------|-------|--------------|-------|
| chat | `chat` | true | `llm.ollama_called=true` · model `qwen2.5:1.5b` |
| explain | `expert` | true | Tool Manager path · `prediction_meta.mutated=false` |
| review | `review` | true | Tool Manager path · `prediction_meta.mutated=false` |

Prediction connector returned `prediction_api_error:KeyError` for sample race on this host (data wiring). Conversation platform still fail-opens with **Read Only** (`mutated=false`) — Prediction AI itself was not modified.

---

## C. Component checklist

| Component | Evidence | Status |
|-----------|----------|--------|
| Conversation API | `/v1/conversation/chat` + `/health` | PASS |
| Conversation Platform | `orchestrator=true` · health `platform.orchestrator` | PASS |
| Review Agent | smoke `agent=review` · health flag ON | PASS |
| Explain Agent | smoke `agent=expert` · mode explain | PASS |
| Personal Chat | `agent=chat` · public BFF Ollama | PASS |
| Knowledge Runtime | health `F_V5_KNOWLEDGE_RUNTIME=true` | PASS |
| Tool Manager | `prediction_meta.via=tool_manager` · `tool_layer=true` | PASS |
| Prediction Read Only | `mutated=false` on explain/review | PASS |
| Security Guard | health `security_guard_always_on` · verify log `security_block` | PASS |

---

## D. Health excerpt

```text
status=ok
selected_model=qwen2.5:1.5b
ollama.reachable=true
agents=[casual, expert, review, chat]
modes=[explain, review, chat]
prediction_read_only=true
```

---

## E. Operational notes

- Full `verify_conversation_v5_production.py` with Ollama ON is slow on t3.small (~45s/turn). Prefer `--verify-only` deploy smoke + targeted curls.
- Upsize EC2 / GPU before switching `CONVERSATION_DEFAULT_MODEL` to `qwen3:8b`.
