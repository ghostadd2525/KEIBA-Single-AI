# ADR-001 — Security Guard Contract

**Status:** Accepted · Version 4 Final Freeze  
**Date:** 2026-07-25  
**Deciders:** Conversation Platform Freeze  
**Related:** Phase 5 Security Guard · Architecture Review R1

---

## Context

Personal Chat および会話経路における情報漏洩・プロンプト注入を防ぐため、Security Guard を常時稼働させる。適用範囲を曖昧なままにすると迂回経路が残る。

---

## Decision

### 責務

| 項目 | 内容 |
|------|------|
| 役割 | ユーザー入力の Block 判定 · 固定応答 · Ollama 呼び出し前の安全ゲート |
| 無効化 | **禁止**（`SECURITY_GUARD_ALWAYS_ON` · Feature Flag で OFF 不可） |
| 変更権限 | Guard 本体の仕様変更は Platform 改訂（新 ADR）を要する |

### 適用契約（V4 Freeze）

| Mode | Guard の強制点 | 効果 |
|------|----------------|------|
| `chat` | Orchestrator **pre-router** hard block | Block 時は Router / Agent / Ollama / History 追加を行わない |
| `chat` | ChatAgent 内 **再検査**（Ollama 直前） | 二重防御 |
| `review` / `explain` / `default`（Casual） | Orchestrator の **履歴ゲート**（`guard_for_history`） | Block 相当メッセージは履歴に載せない。Agent 実行自体の hard abort は V4 では必須としない |
| Knowledge / Tool 呼び出し | **Guard 通過後のみ**を前提とする（Tool Manager は Guard を再実装しない） |

**V4 公式解釈:** Security Guard の **hard block 契約は Personal Chat（`mode=chat`）を第一対象**とする。Review / Explain / Casual は「履歴汚染防止 + 将来の共通 hard block 拡張」とし、V4 Freeze 範囲では chat 偏重を **受理済み設計** とする（Architecture Review R1 の文書解決）。

### 唯一の入口

- `SecurityGuard.check(message) -> GuardResult`
- Orchestrator / ChatAgent からのみ呼び出す

### 唯一の出口

- 許可: 後続パイプラインへ進む
- 拒否: `block_response()` 固定文（Ollama 非呼び出し · `blocked=true`）

### 依存方向

```text
Orchestrator / ChatAgent → SecurityGuard → policy / rules
（Guard は Agent・Tool・Prediction・Knowledge に依存しない）
```

### 禁止事項

1. Guard を Feature Flag で無効化すること
2. Agent / Tool / Knowledge / Prediction から Guard をバイパスして Ollama を呼ぶこと（Chat 経路）
3. Block 応答を LLM で生成すること
4. Guard が Prediction / Ranking / Confidence を参照・変更すること
5. Guard がユーザー固有 Memory を読み書きすること

### Feature Flag

- Security Guard 専用 Flag は **設けない**（常時 ON）
- `F_V4_PERSONAL_CHAT` は Chat Agent の有効化であり、Guard を OFF にしない

### Legacy / 将来

- V4: 上記適用表を契約とする
- V5 候補: 全 mode 共通の pre-agent hard block（新 ADR が必要）

---

## Consequences

- Personal Chat の漏洩対策は契約上保証される
- Review/Explain への hard block 統一は V4 凍結後の別 ADR
- 運用・監査は「chat hard block / 他 mode 履歴ゲート」を前提に記録する
