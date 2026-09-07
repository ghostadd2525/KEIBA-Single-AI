# ADR-010 — Explanation Confidence（Core）

**Status:** Accepted（Architecture Definition） · **Platform Version1 Contract（FROZEN · V109）**  
**Date:** 2026-07-28  
**Version tag:** Version101  
**Parents:** ADR-009（AI Core Completeness） · ADR-003（Prediction Read-Only） · ADR-008（Decision Layer） · V100 Completeness Shadow  
**実装:** 本 ADR は定義のみ。製品コード変更は **禁止**（別 Decision）。  
**凍結:** `docs/adr/PLATFORM-V1-CONTRACT.md` — Core 研究終了。改訂は例外三条件の証明後のみ。

---

## Context

V100 Core Completeness Shadow は、コーパス上の候補フィールド `confidence` 欠落を報告した。  
これは **Prediction Probability / Calibration Confidence** の欠落と解釈されやすいが、ADR-009 の Core 目的（レースを完全に記述する）とは異なる。

混同リスク:

| 誤解 | 問題 |
|---|---|
| Confidence = 勝率 / win_prob | Prediction Score と二重化。ADR-003 と衝突しやすい |
| Confidence = オッズの逆数 | 市場指標であり Core 説明ではない |
| Confidence = Calibration p | V84–V87 で World 主エンジン化は未証明。Core KPI 外 |
| Confidence 欠落 = Core 失敗 | Prediction Confidence を Core が返さないなら欠落ではない |

---

## Decision

### 1. Core は Prediction Confidence を返さない（MUST）

AI Core は次を **返さない / KPI にしない**:

- Prediction Probability としての Confidence  
- Ranking / Score の確信度（勝率校正）  
- オッズ由来の確信度  
- Calibration（ECE/Brier）用の確率信頼度  

これらは Prediction / Calibration / Decision 側の関心事とし、**本 ADR の対象外**とする。

### 2. Core Confidence = Explanation Confidence（MUST）

Core が返す（または将来返す） Confidence は **Explanation Confidence** と定義する。

意味するもの:

| 側面 | 内容 |
|---|---|
| 説明の完全性 | なぜこの World / Near Miss か、必要な要素が揃っているか |
| 説明の一貫性 | Must / Match / Exclusion の論理が矛盾しないか |
| Trace の充足 | Must / Exclusion / Match / Transition / Decision-tree path が保持されているか |
| Must / Exclusion の確定性 | 充足・ギャップ・除外理由が確定して記述できるか |

意味しないもの: 勝率、オッズ、ROI、購入推奨度。

### 3. Confidence 候補軸（Taxonomy）

| ID | 名称 | 要約 |
|---|---|---|
| EC-S | **Semantic Confidence** | 「なぜこのラベルか」を説明できる度 |
| EC-W | **World Confidence** | World ラベル＋契約トレースの確定度 |
| EC-N | **Near Miss Confidence** | unsatisfied 時の Near Miss 記述の確定度（非該当は N/A） |
| EC-T | **Trace Confidence** | Must / Exclusion / Match / Transition トレースの充足度 |

合成 Explanation Confidence（任意）は上記の関数とする（重みは Contract で定義。本 ADR は軸の存在を確定）。

### 4. 層境界（MUST）

```text
Prediction Layer     → Rank / Score のみ（Confidence 確率を Core 出力にしない）
Core Explanation     → Explanation Confidence（本 ADR）
Decision Layer       → Ticket / Skip / 資金（ADR-008）。Explanation Confidence を読んでよいが
                       勝率に再解釈してはならない
```

### 5. V100 再解釈（MUST）

V100 の `confidence:candidate_missing`（Prediction 候補フィールド）は:

- **Core Completeness の必須欠落としては扱わない**（本 ADR 採択後）
- Prediction Confidence を Core が返さないことの確認観測として記録する

Core Completeness の Confidence 関連 KPI は **Explanation Confidence** に置き換える。

---

## Consequences

### Positive

- Confidence 語の多義性を解消  
- ADR-009 Completeness と整合（説明の質）  
- Decision が「確信度＝勝てる」と誤解する経路を遮断  

### Negative / Trade-off

- 既存コード・UI の `confidence` 語が Prediction 意味のまま残る可能性 → 命名分離が必要（実装は別 Decision）  
- Explanation Confidence の数値スケールは Contract で段階導入  

### Rollback

ADR 改訂のみ。製品既定動作は本 ADR 単独では変更しない。

---

## Related

- `docs/research/v101-confidence-contract.md`
- `docs/research/v101-confidence-taxonomy.md`
- `docs/research/v101-governance.md`
- ADR-009 · V100 Completeness Report
