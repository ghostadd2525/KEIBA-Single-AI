# Version 3 — Accuracy Gap Analysis v2

**Date:** 2026-07-24  
**Status:** Gap Analysis COMPLETE · **A-04 実装なし**  
**Control stack:** Lab Baseline v2 = **A-01 Evaluation + A-03 Admission**  
**Baseline:** `v3-lab-baseline-v2-a01-a03` · Hit **255** / Miss **30** / Control OFF **218**  
**Corpus:** `a03-285-*`（`build_a03_accuracy_corpus` · n=285）  
**Artifact:** `research/v3_lab/baselines/accuracy_gap_analysis_v2.json`

---

## 1. 目的

Lab Baseline v2（Hit 255）で残るミスを分類し、**A-04 が解くべき問題を再定義**する。  
新しい Accuracy アルゴリズム・Feature Flag・Production 配線は行わない。

---

## 2. 前提（凍結）

| 項目 | 値 |
|------|-----|
| Representation | Baseline |
| Admission | **A-03** ON |
| Selection | Baseline（identity） |
| Evaluation | **A-01** ON |
| Purchase / Delete | Baseline · 不変 |
| A-02 | Secondary held · スタック外 |
| D1+D2 同時 ON | 禁止 |

未変更: 全アルゴリズム · Feature Flag · V2 Production · Prediction API · UI · Ops · Explainability

---

## 3. 残存ミス一覧（30）

| 層 | n | 代表 race_id 範囲 | winner_rank | 発生ステージ |
|----|---|-------------------|-------------|--------------|
| **Boundary** | 14 | `a03-285-247` … `260` | 3 | **Evaluation** |
| **Reorder** | 10 | `a03-285-261` … `270` | 2 | **Selection** |
| **Delete** | 6 | `a03-285-280` … `285` | 5 | **Delete** |
| Eval | 0 | — | — | （A-01 で回収済） |
| Pool | 0 | — | — | （A-03 で回収済） |

全件一覧・特徴量は JSON artifact を正とする。

### 3.1 Boundary（14）典型サイン

| 項目 | 値 |
|------|-----|
| field_size | 8 |
| top win_prob | ≈0.19 |
| winner win_prob | ≈0.18 |
| wp 差 | ≈0.01（混雑） |
| 解釈 | トップ近傍同点 · D1 校正では入れ替わらない |

### 3.2 Reorder（10）典型サイン

| 項目 | 値 |
|------|-----|
| field_size | 8 |
| top / winner wp | ≈0.210 / 0.205 |
| 解釈 | 枠内想定だが順序副作用で top pick が外れる |

### 3.3 Delete（6）

`purchase_eligible=false`。Accuracy 非対象（製品境界）。

---

## 4. ステージ別帰属

```text
Miss 30
├── Evaluation …… 14 (Boundary)
├── Selection …... 10 (Reorder)
└── Delete ……… 6
```

| ステージ | 残 miss | Baseline v2 での状態 | 改善余地 |
|----------|---------|----------------------|----------|
| Representation | 0 | Baseline | 低（本残差の主因ではない） |
| Admission | 0 | A-03 採用済 | 飽和（Pool 0） |
| **Selection** | **10**（+Boundary 転用余地） | **Baseline identity** | **高（A-04 提案）** |
| Evaluation | 14 | A-01 採用済 | 中〜高だが A-02 再スタックは禁止/破壊的 |
| Purchase | 0 | Baseline | 触らない |
| Delete | 6 | 不変 | **なし** |

---

## 5. 原因分類

| 原因 ID | 層 | n | 内容 |
|---------|----|---|------|
| `I-Boundary_crowded_near_top` | Boundary | 14 | 混雑場で相対区別不能（A-02 形状） |
| `I-Reorder_order_side_effect` | Reorder | 10 | 順序/圧縮副作用（Selection 主因） |
| `purchase_delete_boundary` | Delete | 6 | 購入削除境界 |

### 5.1 A-02 との関係（実証）

同一コーパスでの参照アーム（分析のみ・採用しない）:

| アーム | Hit | 注記 |
|--------|-----|------|
| A-01 + A-03（Baseline v2） | **255** | 公式 |
| A-02 + A-03 | 251 | Boundary+Reorder 24 を回収するが **Eval 28 を破壊** |
| A-01 + A-02 + A-03 | 255 | D2 追加効果なし（Baseline v2 と同値） |

含意: 残 24 は A-02 Evaluation 形状だが、**Evaluation を重ねても Baseline v2 を超えられない**。

---

## 6. 改善余地の推定

| バケット | n | 理論上の Hit 寄与 | 実現性 |
|----------|---|-------------------|--------|
| Boundary + Reorder | 24 | +24 → Hit **279** | 条件付き高（churn=0 必須） |
| Delete | 6 | 0 | 対象外 |
| 天井（本 corpus） | — | **279**（285−6） | Delete 除去後 |

Hard Gate 想定（A-04 設計時）: Hit > **255** ∧ churn vs Baseline v2 = **0**。

---

## 7. 変更すべきステージ（1 つのみ）

> **Selection**

理由:

1. Evaluation Primary（A-01）と Admission Primary（A-03）は Lab Configuration Freeze 済  
2. A-02（Evaluation）は残 24 を回収できるが Eval を破壊し、D1 同時 ON でも増分なし  
3. 公式スタック上 Selection だけが **Accuracy 残差に対して identity のまま**  
4. Reorder 10 は Selection 発生ステージそのもの。Boundary 14 も候補場内の並べ替えで到達可能な隣接問題

**禁止提案:** Evaluation の再介入（D2 採用 / D1+D2 同時 / A-01 置換）を A-04 の第一選択にしない。

---

## 8. A-04 問題定義（要約）

詳細: [`v3-a04-problem-definition.md`](./v3-a04-problem-definition.md)

> Lab Baseline v2（A-01+A-03）を壊さず、**Selection のみ**を変更して Boundary+Reorder 残差（最大 24）を回収する。

---

## 9. 提出物

| 提出物 | パス |
|--------|------|
| Gap Analysis Report | 本ドキュメント |
| Updated Miss Taxonomy | [`v3-miss-taxonomy-gap-v2.md`](./v3-miss-taxonomy-gap-v2.md) |
| A-04 Problem Definition | [`v3-a04-problem-definition.md`](./v3-a04-problem-definition.md) |
| Research Roadmap 更新 | [`v3-accuracy-phase2-research-roadmap.md`](./v3-accuracy-phase2-research-roadmap.md) · [`v3-experiment-roadmap.md`](./v3-experiment-roadmap.md) |
| Research Report 更新 | [`v3-accuracy-phase2-research-report.md`](./v3-accuracy-phase2-research-report.md) |
| JSON | `research/v3_lab/baselines/accuracy_gap_analysis_v2.json` |

---

## 10. 停止

**Accuracy Gap Analysis v2 完了。ここで停止する。**  
A-04 の実装・Design Proposal 実装・Flag 追加には着手しない。
