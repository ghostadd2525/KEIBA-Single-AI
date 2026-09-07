# ADR-006 — Memory Layer Contract（V6 Phase 2）

**Status:** Accepted  
**Date:** 2026-07-25  
**Deciders:** Conversation V6 Phase 2  
**Related:** ADR-005 · V4 Platform Freeze · V6 Phase 1 Knowledge Contents

---

## Context

長期ユーザー Memory を Conversation AI に追加する。  
Version 4 Platform / Knowledge Runtime / Tool Manager / History は凍結のまま、  
**Consent-only Long-term Memory** を Platform 外レイヤーとして導入する。

---

## Decision

### 責務

| Layer | 責務 | 非責務 |
|-------|------|--------|
| Memory Store | Consent 済み長期 Preference / Profile / Settings / Favorite | History · Prediction · Knowledge |
| Memory Policy | 保存可能 / 禁止判定 | 自動保存 |
| Consent Manager | 「覚えて」等の明示同意検出 | 暗黙同意の推定 |
| Memory Manager | Candidate → Consent → Store フロー | V4 Orchestrator 代替 |
| Memory Retriever | Conversation Context 用の読出 | RAG / Knowledge 検索 |
| Memory Tool | 覚えて / 忘れて / 一覧 / 全削除 | Tool Manager 登録 |
| Memory Gateway | `conversation.chat` 入口前段の接続 | Agents / History 改変 |

### 保存可能

- ニックネーム · 呼び方
- 好きな競馬場 · 騎手 · 馬
- 説明スタイル · 回答の長さ
- Conversation 設定
- ユーザーが「覚えて」と明示した許容内容

### 保存禁止

Prediction · Ranking · Confidence · Security · API · Feature Flag ·  
System Prompt · Secrets · Conversation 履歴 · 一時的な雑談（同意なし）

### フロー

```text
Conversation
  → Memory Candidate
  → User Consent（明示「覚えて」のみ）
  → Memory Store
  → Memory Retriever
  → Conversation Context
```

### Feature Flag

| Flag | 既定 | 意味 |
|------|------|------|
| `F_V6_MEMORY` | **OFF** | Memory Platform 有効化 |

OFF 時は Gateway 完全ノーオペ。自動保存経路は存在しない。

### 分離規則

1. Conversation History と Memory は型・ストレージ・API を共有しない
2. History → Memory の暗黙昇格は禁止
3. Knowledge Source / Runtime にユーザー Memory を混ぜない
4. Memory Tool は Tool Manager / Capability に登録しない
5. V4 Orchestrator · Agents · Security Guard · Prediction は変更しない

### 配線（許可される最小侵食）

| 場所 | 内容 |
|------|------|
| `conversation/__init__.py` | Gateway 前段（Flag ON 時のみ） |
| `v4/flags.py` | `F_V6_MEMORY` 加算（V5 と同型） |

---

## Consequences

- Memory は Long-term · Consent-only として正式導入可能
- 本番は Flag OFF のまま安全にデプロイできる
- 凍結コンポーネントの再 Freeze 改訂は不要（本 ADR が Memory 範囲を定義）
