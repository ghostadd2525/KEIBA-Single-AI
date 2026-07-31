# Version99 — Completeness Evaluation

**Date:** 2026-07-28  
**Status:** Evaluation Frame（測定設計）· KPI 閾値の本番採用は別 Decision  
**Parent:** ADR-009 / V99 Charter  
**Locks:** Prediction / World / Trigger の本フレームによる無断改変禁止。評価は観測・欠落検知が主。

---

## 目的

Core 研究の成功を **ROI ではなく Completeness** で測る。

対象レース: 原則 **全レース**（285R コーパスおよび将来の全開催）。

---

## 1. Prediction Completeness

### 問い

全出走馬について、公式 Prediction（Rank / Score）が欠落なく、再現可能に付与されているか？

### 観測指標（設計）

| ID | 指標 | 定義 |
|---|---|---|
| PC-1 | rank_coverage | 出走馬のうち `model_rank` が有効な割合（レース平均 / 全体） |
| PC-2 | score_coverage | `win_prob`（または公式 score）が有効な割合 |
| PC-3 | top1_defined | レースごとに predicted Top1 が一意に定義できる割合 |
| PC-4 | fingerprint_stable | 同一入力で prediction fingerprint が安定する割合 |
| PC-5 | field_alignment | field_size と runners 件数の一致率 |

### 成功の意味

「買って勝てる」ではなく、**Decision が読める完全な予測バンドル**であること。

### 非指標

Ticket ROI / Purchase Hit / Buy Rate（Decision 側）。

---

## 2. World Completeness

### 問い

全レースに、契約どおりの World（または `unsatisfied`）が付与され、MATCH / Exclusion トレースが欠落していないか？

### 観測指標（設計）

| ID | 指標 | 定義 |
|---|---|---|
| WC-1 | label_coverage | 全レースに `cew_world`（または同等）が付く割合 → 目標 1.0 |
| WC-2 | trace_coverage | `decision_trace`（World 別 must/exclude/gaps）が存在する割合 |
| WC-3 | match_consistency | `match` ⇔ must∧¬exclude の論理整合率 |
| WC-4 | positive_world_rate | Positive MATCH 率（観測。増やすこと自体は目的にしない） |
| WC-5 | transition_coverage | `world_transition` / trigger_path が記録される割合 |
| WC-6 | expected_strategy_present | World 既知なら V75 Expected Strategy 参照が解決できる割合 |

### 成功の意味

ラベルの **欠落と論理破綻がない**こと。unsatisfied を減らすことは **World Completeness の主目的ではない**（V96 と同趣旨）。

### 非指標

World 別 ROI、券種別成績。

---

## 3. Near Miss Completeness

### 問い

`unsatisfied` について、Near Miss / Pure Residual 分離と、近接 World・Must Gap·Exclusion Reason·Affinity が欠落なく保持されるか？

### 観測指標（設計）

| ID | 指標 | 定義 |
|---|---|---|
| NMC-1 | class_coverage | unsatisfied 全件が `NEAR_MISS` \| `PURE_RESIDUAL` に分類される割合 → 目標 1.0 |
| NMC-2 | near_world_coverage | NEAR_MISS で `near_world`（primary）が非 null の割合 |
| NMC-3 | must_gap_coverage | 各対象 World の `must_gaps` がトレースから復元できる割合 |
| NMC-4 | exclusion_reason_coverage | NEAR_MISS で Exclusion Reason が1つ以上保持される割合 |
| NMC-5 | affinity_vector_coverage | core/midupper/midhole/rank7 の Affinity 4値が揃う割合 |
| NMC-6 | taxonomy_version_present | Taxonomy / Affinity バージョンメタの付与率 |

### 成功の意味

「Near Miss で儲かった」ではなく、**残余の記述が Decision に渡せるほど完全**であること。

### 非指標

Near Miss ROI、Affinity-aware Skip の PnL（V97/V98 は Decision 記録）。

---

## 4. 合否の扱い（研究ゲート案）

| Completeness | ゲート案（研究） |
|---|---|
| Prediction | PC-1..3 がコーパスで欠損ゼロに近い |
| World | WC-1..3 が欠損・論理破綻ゼロ |
| Near Miss | NMC-1..5 が unsatisfied 全件で充足 |

閾値の本番採用・自動 fail は **別 Decision**。本ドキュメントは評価軸の固定まで。

---

## 5. レポート出力（将来 Shadow）

```text
CompletenessReport
  prediction: { PC-1..5, status }
  world:      { WC-1..6, status }
  near_miss:  { NMC-1..6, status }
  n_races
  generated_at
```

Core 研究の Go/No-Go は本レポートを一次資料とする。ROI 表は添付しない（Decision 別紙）。

---

## 関連

- ADR-009
- `v99-core-completeness-charter.md`
- V95 Taxonomy · V96 Affinity · V94 Clustering
