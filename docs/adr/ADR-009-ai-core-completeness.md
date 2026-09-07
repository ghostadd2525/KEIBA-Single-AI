# ADR-009 — AI Core Completeness（利益非目的）

**Status:** Accepted（Architecture / Research Charter） · **Platform Version1 Contract（FROZEN · V109）**  
**Date:** 2026-07-28  
**Version tag:** Version99  
**Parents:** ADR-003（Prediction Read-Only） · ADR-008（Decision Layer） · V94–V98（Near Miss / Affinity / ROI 分離の実証）  
**実装:** 本 ADR は憲章。製品コード変更は別 Decision。  
**凍結:** `docs/adr/PLATFORM-V1-CONTRACT.md` — Core 研究終了。改訂は例外三条件の証明後のみ。

---

## Context

V88–V98 により次が確定した。

| 層 | 知見 |
|---|---|
| Prediction | World で順位改善は不成立（ADR-008） |
| Decision | World / Near Miss Metadata は Decision 入力になり得る |
| Affinity→Decision | Near Miss Affinity の Risk 抑制に **Decision 価値なし**（V97 NO_VALUE） |
| Near Miss ROI | 利益条件は ROI Pattern で分解可能（V98）だが **それは Decision/購入側の関心事** |

混同リスク: Core 研究が ROI・券種・Skip・資金配分を最適化しようとすると、  
**「最も正確な World 記述」** という Core 本来の目的から逸脱する。

---

## Decision

### 1. AI Core の目的（MUST）

AI Core は **利益を最大化しない**。

全レースについて、次を **最も正確に返す** ことを目的とする。

| 出力 | 意味 |
|---|---|
| **World** | CEW / 契約 MATCH ラベル（既存 Trigger 契約） |
| **Near Miss** | unsatisfied 時の Exclusion 近接 Metadata（V95 Taxonomy） |
| **Affinity** | 各 World への Must 近さ（V96・観測）。CEW 書き換え権限を持たない |
| **Transition** | Legacy/経路遷移・`world_transition` 等の説明可能トレース |
| **Expected Strategy** | 当該 World/Near Miss が主張する **読み方・優先軸**（V75 Contract の Selector 意図）。券種・金額ではない |
| **Explanation Confidence** | 説明の完全性・一貫性・Trace 充足（**ADR-010**）。勝率/オッズ/Calibration ではない |

### 2. Decision の Owner（MUST）

| 関心事 | Owner |
|---|---|
| ROI / 券種 / Skip / 資金配分 / Ticket / Risk 購入ゲート | **Single AI / Win5 AI（Decision Layer）** |
| Core 出力の消費 | Decision が read-only で読む |

ADR-008 を維持・精密化する: Decision は Core の Completeness 出力を入力にし、購入最適化は Decision 側のみ。

### 3. Core 研究対象外（MUST NOT）

| 禁止（Core KPI / Core 最適化目的） |
|---|
| Ticket ROI / PnL 最大化 |
| 券種最適化 |
| Skip Policy 最適化（購入見送り） |
| 資金配分 / Budget Allocation |
| Buy Rate を上げるためのラベル改変 |

V93 Betting / V97 Affinity Decision / V98 ROI Pattern は **Decision 研究**として記録し、**Core Completeness の成功指標にしない**。

### 4. 今後の評価対象（MUST）

| 評価軸 | 定義（概要） |
|---|---|
| **Prediction Completeness** | 公式 Rank/Score が欠損なく、再現可能に全出走へ付与されているか |
| **World Completeness** | 全レースに契約どおりの World（または unsatisfied）が付与され、MATCH/Exclusion トレースが欠落しないか |
| **Near Miss Completeness** | unsatisfied について Near Miss / Pure Residual 分離、near_world、Must Gap、Exclusion Reason が欠落なく保持されるか |

詳細指標は `docs/research/v99-completeness-evaluation.md`。

---

## 層図（更新）

```text
┌──────────────────────────────────────────────┐
│ AI Core                                        │
│  Prediction Completeness                       │
│  World / Near Miss / Affinity / Transition      │
│  Expected Strategy（読み方・非購入）              │
│  ※ ROI・券種・Skip・資金配分は出さない            │
└───────────────────┬──────────────────────────┘
                    │ read-only bundle
                    ▼
┌──────────────────────────────────────────────┐
│ Single AI / Win5 AI — Decision Layer           │
│  Ticket · Skip · 資金配分 · ROI 最適化           │
│  （ADR-008）                                   │
└──────────────────────────────────────────────┘
```

---

## Consequences

### Positive

- Core と Decision の KPI 混線を防ぐ  
- Near Miss / Affinity を「正確な記述」として残しつつ、購入最適化から切り離せる  
- V97 NO_VALUE を Core 失敗と誤解しない（Decision 仮説の否定）

### Negative / Trade-off

- Core 単体では「勝てるか」を答えられない（意図的）  
- Completeness 指標の運用定義・閾値は追加整備が必要

### Rollback

憲章の撤回は ADR 改訂のみ。コード既定動作は本 ADR 単独では変更しない。

---

## Related

- `docs/research/v99-core-completeness-charter.md`
- `docs/research/v99-completeness-evaluation.md`
- `docs/research/v99-governance.md`
- ADR-003 · ADR-008 · ADR-010（Explanation Confidence） · V95 Taxonomy · V96 Affinity · V97/V98（Decision 側記録）
