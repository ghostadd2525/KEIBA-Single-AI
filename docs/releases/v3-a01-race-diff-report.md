# Version 3 — A-01 Race Diff Report

**Date:** 2026-07-24  
**Corpus:** Lab synthetic 285R（`a01-285-*`）  
**Flag:** Control = all OFF / Treatment = `F_V3_RANK_D1_ENABLED`  
**Artifact:** `research/v3_lab/baselines/a01_validation/a01_race_diff.json`

---

## 1. 集計

| 区分 | 件数 |
|------|------|
| Improved（Control miss → Treatment hit） | **28** |
| Worsened（Control hit → Treatment miss / churn） | **0** |
| Unchanged hit | 218 |
| Unchanged miss | 39 |
| Total | 285 |

### 改善の層別内訳

| miss_layer | Improved |
|------------|----------|
| Eval | **28** |
| その他 | 0 |

→ D1 の効果が Evaluation 層の recoverable miss に限定されていることを確認。

---

## 2. バケット詳細（rank710 / rank46 / other）

| Bucket | Control | Treatment | Δ |
|--------|---------|-----------|---|
| rank710 | 9 | 9 | 0 |
| rank46 | 6 | 6 | 0 |
| other | 52 | 24 | **−28** |

解釈: Treatment の +28 Hit はすべて Control の `other` miss から転換。rank710 / rank46 は D1 では回収していない（設計どおり Eval-layer 校正の範囲）。

---

## 3. 悪化レース一覧

なし（`worsened_races = []` / `churn_hit = 0`）。

---

## 4. 改善レース一覧（28）

パターン: Control は `model_rank=1` を pick、Treatment は winner（多くは rank=2）へ再校正。

| race_id | layer | winner | C pick | T pick | C odds | T odds |
|---------|-------|--------|--------|--------|--------|--------|
| a01-285-219 | Eval | H218-2 | H218-1 | H218-2 | 4.8 | 3.1 |
| a01-285-220 | Eval | H219-2 | H219-1 | H219-2 | 4.8 | 3.1 |
| a01-285-221 | Eval | H220-2 | H220-1 | H220-2 | 4.8 | 3.1 |
| a01-285-222 | Eval | H221-2 | H221-1 | H221-2 | 4.8 | 3.1 |
| a01-285-223 | Eval | H222-2 | H222-1 | H222-2 | 4.8 | 3.1 |
| a01-285-224 | Eval | H223-2 | H223-1 | H223-2 | 4.8 | 3.1 |
| a01-285-225 | Eval | H224-2 | H224-1 | H224-2 | 4.8 | 3.1 |
| a01-285-226 | Eval | H225-2 | H225-1 | H225-2 | 4.8 | 3.1 |
| a01-285-227 | Eval | H226-2 | H226-1 | H226-2 | 4.8 | 3.1 |
| a01-285-228 | Eval | H227-2 | H227-1 | H227-2 | 4.8 | 3.1 |
| a01-285-229 | Eval | H228-2 | H228-1 | H228-2 | 4.8 | 3.1 |
| a01-285-230 | Eval | H229-2 | H229-1 | H229-2 | 4.8 | 3.1 |
| a01-285-231 | Eval | H230-2 | H230-1 | H230-2 | 4.8 | 3.1 |
| a01-285-232 | Eval | H231-2 | H231-1 | H231-2 | 4.8 | 3.1 |
| a01-285-233 | Eval | H232-2 | H232-1 | H232-2 | 4.8 | 3.1 |
| a01-285-234 | Eval | H233-2 | H233-1 | H233-2 | 4.8 | 3.1 |
| a01-285-235 | Eval | H234-2 | H234-1 | H234-2 | 4.8 | 3.1 |
| a01-285-236 | Eval | H235-2 | H235-1 | H235-2 | 4.8 | 3.1 |
| a01-285-237 | Eval | H236-2 | H236-1 | H236-2 | 4.8 | 3.1 |
| a01-285-238 | Eval | H237-2 | H237-1 | H237-2 | 4.8 | 3.1 |
| a01-285-239 | Eval | H238-2 | H238-1 | H238-2 | 4.8 | 3.1 |
| a01-285-240 | Eval | H239-2 | H239-1 | H239-2 | 4.8 | 3.1 |
| a01-285-241 | Eval | H240-2 | H240-1 | H240-2 | 4.8 | 3.1 |
| a01-285-242 | Eval | H241-2 | H241-1 | H241-2 | 4.8 | 3.1 |
| a01-285-243 | Eval | H242-2 | H242-1 | H242-2 | 4.8 | 3.1 |
| a01-285-244 | Eval | H243-2 | H243-1 | H243-2 | 4.8 | 3.1 |
| a01-285-245 | Eval | H244-2 | H244-1 | H244-2 | 4.8 | 3.1 |
| a01-285-246 | Eval | H245-2 | H245-1 | H245-2 | 4.8 | 3.1 |

※ 全 285R の status 付き一覧は JSON artifact の `races[]` を参照。

---

## 5. churn 詳細

| 項目 | 値 |
|------|-----|
| churn_hit | 0 |
| churn_races | [] |
| pick 変更かつ hit→miss | 0 |

Control の 218 Hit は Treatment でもすべて維持。
