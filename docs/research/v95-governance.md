# Version95 — Governance（Residual Decision Taxonomy）

**Date:** 2026-07-28  
**Status:** Design ONLY — **実装禁止**  
**Parents:** V94 · V95 Taxonomy/Policy · ADR-008

---

## Decision Gate

| Item | Value |
|---|---|
| Action Type | Residual Decision Taxonomy（設計） |
| Implementation Required | **No** |
| Deployment Required | No |
| Configuration Required | No |
| Production Required | No |
| Rollback Required | No |
| New World Authorized | **No** |
| CEW / Trigger Change | **No** |
| Prediction Change | **No** |
| Risk | Low（文書のみ） |
| Expected Next Action | 承認後に限り Shadow 実装 Decision（V96+）。未承認のままコード追加禁止 |

---

## 採択事項（本フェーズ）

1. `unsatisfied` は **World のまま Residual**。内訳は **Decision Metadata**。  
2. Taxonomy: `NEAR_MISS`（Exclusion） / `PURE_RESIDUAL`（Must全失敗）。  
3. Near Miss は `near_world` に応じ **Risk / Pool / Explanation** のみ差分。  
4. Ticket は両クラスとも **保守**（勝ち筋化禁止・DL-C6 維持）。  
5. Pure Residual は V88 保守 Policy を継承。

---

## 硬制約

| ID | 制約 |
|---|---|
| G95-1 | Prediction / Ranking / Score 変更禁止 |
| G95-2 | World Meaning / Trigger / CEW 生成規則変更禁止 |
| G95-3 | Near Miss を新 CEW World として追加禁止 |
| G95-4 | Near Miss に本採用 World の Ticket Strategy コピー禁止 |
| G95-5 | 本フェーズでの `app/decision/*` 実装・Flag 追加禁止 |
| G95-6 | PE / Production 配線禁止 |

---

## ADR-008 追記候補（設計メモ・未コミット）

将来 ADR 改訂時の文言案（本 V95 では ADR 本体を変更しない）:

> **DL-C6a:** `unsatisfied` の Decision Metadata として `NEAR_MISS` / `PURE_RESIDUAL` を認めてよい。  
> Metadata は Risk / Pool / Explanation にのみ作用し、Positive Ticket Strategy を正当化しない。

---

## 成果物チェック

| 成果物 | Path | Status |
|---|---|---|
| Residual Taxonomy | `docs/research/v95-residual-taxonomy.md` | Done |
| Decision Policy | `docs/research/v95-decision-policy.md` | Done |
| Governance | `docs/research/v95-governance.md` | Done |
| 実装 | — | **禁止（未着手）** |

---

## 次 Decision（参考・起動しない）

| 候補 | 内容 | 前提 |
|---|---|---|
| V96 Shadow | Metadata 付与＋ Explain/Risk/Pool 差分の Shadow 評価 | V95 承認 |
| Exclusion 監査 | core Near Miss の Forbidden 条件 | Taxonomy とは別ゲート |
| World 追加 | — | **継続禁止** |
