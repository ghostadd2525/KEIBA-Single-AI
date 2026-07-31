# Version 4 — Conversation AI Phase 6 · Conversation History

**Date:** 2026-07-25  
**Status:** Implemented  
**Scope:** セッション単位の短期 Conversation History のみ  
**Out of scope:** Memory · RAG · Tool · UI · Database · Prediction API

---

## 1. Conversation History

| 項目 | 内容 |
|------|------|
| 対象 | User Message / Assistant Message のみ |
| 単位 | `session_id` |
| 上限 | 設定可能（既定 20） |
| 淘汰 | FIFO |
| 永続化 | **禁止**（プロセスメモリのみ） |
| 共通 | Personal Chat / Review / Explain |

Security Guard 通過後の内容のみ保持（Guard 自体は変更なし）。

---

## 2. Components

| 提出物 | Path |
|--------|------|
| Conversation History | `v4/history/models.py` |
| History Manager | `v4/history/manager.py` |
| ConversationContext | `v4/context/conversation_context.py` |
| Prompt Builder | `build_chat` / `build_review` / `build_explain` に履歴ブロック |

設定:

- `CONVERSATION_HISTORY_MAX_MESSAGES`（既定 20）
- `CONVERSATION_HISTORY_PROMPT_TURNS`（既定 8 · Prompt に載せる直近件数）

---

## 3. Sequence Diagram

```mermaid
sequenceDiagram
  participant C as Client
  participant O as Orchestrator
  participant G as Security Guard
  participant H as History Manager
  participant A as Chat/Review/Explain
  participant P as Prompt Builder

  C->>O: session_id + message
  O->>G: check(message)
  alt blocked
    G-->>O: block
    Note over H: 履歴に追加しない
    O-->>C: 固定文
  else allowed
    O->>H: prompt_history(session)
    H-->>O: 直近 N 件
    O->>A: handle(+ history)
    A->>P: build_*(history)
    P-->>A: prompt
    A-->>O: reply
    O->>H: append user + assistant
    O-->>C: reply + conversation meta
  end
```

---

## 4. Stop

Conversation History 実装完了。Memory / Prediction API / RAG / Tool / UI には着手しない。
