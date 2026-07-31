# Memory Specification — V6 Phase 2

**Status:** Active  
**Flag:** `F_V6_MEMORY`（既定 OFF）  
**ADR:** [ADR-006](../adr/ADR-006-memory-layer-contract.md)

---

## 1. 目的

Conversation AI に **長期 Memory** を追加する。  
ユーザーが明示的に保存を許可した情報のみを保持する。AI の自動記憶は禁止。

---

## 2. 責務境界

| 保持する | 保持しない |
|----------|------------|
| Preferences | Prediction |
| Profile | Ranking / Confidence |
| Conversation Settings | Security / API / Secrets |
| Favorite | Feature Flag / System Prompt |
| 「覚えて」明示内容 | Conversation History / 一時雑談 |
| | Knowledge 共通知識 |

---

## 3. コンポーネント

| 名称 | パス | 役割 |
|------|------|------|
| Memory Store | `app/conversation/v6/memory/store.py` | ユーザー単位 JSON 永続 |
| Memory Retriever | `.../retriever.py` | Context 読出 |
| Memory Manager | `.../manager.py` | Candidate→Consent→Store |
| Memory Policy | `.../policy.py` | 許可/禁止 |
| Consent Manager | `.../consent.py` | 明示同意検出 |
| Memory Tool | `.../tool.py` | ユーザー操作（Tool Manager 非登録） |
| Memory Gateway | `.../gateway.py` | Conversation 入口接続 |

---

## 4. ユーザー操作

| 発話例 | 動作 |
|--------|------|
| 「ニックネームは太郎って覚えて」 | Consent → 保存 |
| 「東京競馬場を忘れて」 | 該当削除 |
| 「私について何を覚えてる？」 | 一覧 |
| 「全部忘れて」 | 全削除 |
| 「好きな馬はディープです」（覚えて無し） | **保存しない** |

---

## 5. Consent Flow

```text
ユーザー発話
    │
    ▼
ConsentManager.classify_intent
    │
    ├─ remember ──► Policy.extract_candidate
    │                   │
    │                   ├─ rejected ──► 保存しない + 理由
    │                   └─ ok + consent ──► Store.upsert
    │
    ├─ forget_one / forget_all / list ──► 各操作
    │
    └─ none ──► Memory 書込なし（通常 Conversation へ）
```

**不変条件:** `consent=False` のレコードは Store が受理しない。

---

## 6. Conversation Context 注入

`F_V6_MEMORY=ON` かつ通常発話時:

1. Retriever が同意済み Memory を取得
2. Gateway が message 先頭へ `[User Memory — consented long-term only]` ブロックを付与
3. V4 Agents / History API は変更しない（入口ファサードのみ）

Memory 操作応答は Gateway が短絡し、`history_touched=false`。

---

## 7. ストレージ

- 場所: `services/win5-ai/var/memory/{user_id}.json`（`CONVERSATION_MEMORY_DIR` で上書き可）
- History（プロセス FIFO）とは別
- 再起動後も残る（Long-term）

---

## 8. Feature Flag

```bash
F_V6_MEMORY=OFF   # 既定 · 本番も当面 OFF 推奨
F_V6_MEMORY=ON    # Consent フロー有効
```
