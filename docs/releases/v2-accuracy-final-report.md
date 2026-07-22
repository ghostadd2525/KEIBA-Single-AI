# Version 2 Accuracy — Final Report

**Date:** 2026-07-22  
**Status:** **検証終了**  
**Corpus:** 285R（labeled_test）  
**Git SHA（全 Experiment 共通）:** `7732f06e8d606d31d1deb338aa306d670a5e2576`  
**判定受領:** PE-V2-A **PASS** / RP-V2-A **FAIL** / CE-V2-A **FAIL**

| 提出物 | パス |
|--------|------|
| 本 Final Report | `docs/releases/v2-accuracy-final-report.md` |
| Experiment Summary CSV | `compare/v2_accuracy_experiment_summary.csv` |
| Roadmap Update | `docs/releases/v2-accuracy-v3-roadmap.md` |

**関連 AB レポート:**

| Experiment | レポート |
|------------|----------|
| PE-V2-A | `docs/ops/v2-pe-v2-a-ab-report.md` |
| RP-V2-A | `docs/ops/v2-rp-v2-a-ab-report.md` |
| CE-V2-A | `docs/ops/v2-ce-v2-a-ab-report.md` |

---

## 0. エグゼクティブサマリー

Version 2 Accuracy は、Phase255 Final（Hit **216**）を起点に、AI Core のみを Feature Flag 付きで検証した。

| 結果 | 内容 |
|------|------|
| **採用** | **PE-V2-A のみ**（Hit 216→**218**） |
| **不採用** | RP-V2-A（効果ゼロ）、CE-V2-A（Hit 悪化 + churn） |
| **最終 Hit** | **218**（PE ロック構成） |
| **検証** | **終了** — 追加 Accuracy V2 Facet は実施しない |

---

## 1. Experiment 一覧

| # | Experiment ID | Facet | Flag | Control | Treatment | STATUS |
|--:|---------------|-------|------|---------|-----------|--------|
| 1 | `v2-pe-v2-a-285r-ab` | **PE-V2-A** | `WIN5_POOL_ENTRY_V2_ENABLED` | Phase255（全 V2 OFF） | PE ON | **PASS** |
| 2 | `v2-rp-v2-a-285r-ab` | **RP-V2-A** | `WIN5_REPICK_V2_ENABLED` | PE ON（Hit=218） | PE + RP | **FAIL** |
| 3 | `v2-ce-v2-a-285r-ab` | **CE-V2-A** | `WIN5_CE_V2_ENABLED` | PE ON（Hit=218） | PE + CE-A | **FAIL** |

**実施順:** PE → RP →（RP FAIL 後に RP を主要候補除外）→ CE-A。  
**未実施:** CE-V2-C / PE-V2-B/C / RO-V2（V2 検証終了のため持ち越し）。

---

## 2. メトリクス比較

### 2.1 一覧表（Control → Treatment）

| Experiment | Hit | Purchase | rank710 | other | rank46 | Winner in Pool率 | churn_hit |
|------------|----:|---------:|--------:|------:|-------:|-----------------:|----------:|
| **PE-V2-A** | 216→**218** | 189→187 | 15→14 | 19→18 | 35→35 | 0.947→**0.961** | **0** |
| **RP-V2-A** | 218→218 | 187→187 | 14→14 | 18→18 | 35→35 | 0.961→0.961 | **0** |
| **CE-V2-A** | 218→**216** | 187→186 | 14→**16** | 18→18 | 35→35 | 0.961→**0.947** | **2** |

正本 CSV: `compare/v2_accuracy_experiment_summary.csv`

### 2.2 Δ（Treatment − Control）

| Experiment | ΔHit | ΔPurchase | Δrank710 | Δother | Δrank46 | ΔWIP率 | churn |
|------------|-----:|----------:|---------:|-------:|--------:|-------:|------:|
| PE-V2-A | **+2** | −2 | −1 | −1 | 0 | **+0.014** | 0 |
| RP-V2-A | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CE-V2-A | **−2** | −1 | +2 | 0 | 0 | **−0.014** | **2** |

### 2.3 Hard Gate（各 Experiment）

| Experiment | Hard Gate | 結果 |
|------------|-----------|------|
| PE-V2-A | Hit > **216** | **達成**（218） |
| RP-V2-A | Hit > **218** | **未達**（218） |
| CE-V2-A | Hit > **218** かつ churn_hit = 0 | **未達**（216 / churn=2） |

---

## 3. 採用／不採用理由

### 3.1 PE-V2-A — **採用**

| 項目 | 内容 |
|------|------|
| 効果 | Hit +2、Winner in Pool 270→274、rank710/other 改善 |
| 副作用 | Purchase −2（記録済・Hard Gate 外）。churn_hit=0 |
| 理由 | Layer1（Pool/Entry）の Deep-rank 入場緩和が、Hard Gate を満たし下流に候補を供給した |
| Flag | `WIN5_POOL_ENTRY_V2_ENABLED` — **Version 2 Accuracy 最終構成で ON** |

### 3.2 RP-V2-A — **不採用**

| 項目 | 内容 |
|------|------|
| 効果 | Hit Δ0、Winner Rescue **0/11**、fired_tx=5（既存 Hit のみ） |
| 理由 | NEAR 系 Rescue Trigger が G1 に届かない（11/11 が `no_near_candidate` を含む）。パラメータ調整では足りず **Trigger 自体が不足** |
| 方針 | Version 2 Accuracy の**主要改善候補から除外**（再 AB・Facet C 相当の RP 再挑戦なし） |
| Flag | `WIN5_REPICK_V2_ENABLED` — **既定 OFF 維持** |

### 3.3 CE-V2-A — **不採用**

| 項目 | 内容 |
|------|------|
| 効果 | Hit −2、WIP率悪化、rank710 悪化、churn=2 |
| churn レース | `2024-01-28-小倉-11` / `2025-12-28-中山-10` |
| 理由 | Softmax 温度較正（temp=0.92）は既得 Hit を崩し、Hard Gate 両条件を満たさない |
| 方針 | Facet C には進まない。CE-V2 全体を V2 採用構成から外す |
| Flag | `WIN5_CE_V2_ENABLED` — **既定 OFF 維持** |

---

## 4. Version 2 Accuracy の最終構成

```text
Version 2 Accuracy Final Stack
│
├─ Phase255 Final（V1.1 Baseline）          【固定】
├─ PE-V2-A（WIN5_POOL_ENTRY_V2_ENABLED=ON） 【採用】
├─ RP-V2-*                                    【不採用・OFF】
└─ CE-V2-*                                    【不採用・OFF】
```

| 層 | コンポーネント | 最終判断 |
|----|----------------|----------|
| Layer1 Pool/Entry | **PE-V2-A** | **採用** |
| Layer2 RePick | RP-V2-A（他 Facet 含む） | **不採用** |
| Layer3 Evaluation | CE-V2-A（Facet C 未実施） | **不採用** |
| Delete | — | **変更禁止（不変）** |

### 4.1 最終メトリクス（採用構成）

| 指標 | Phase255 | **V2 Final（PE のみ）** |
|------|--------:|------------------------:|
| Hit | 216 | **218** |
| Purchase | 189 | **187** |
| rank710 | 15 | **14** |
| other | 19 | **18** |
| rank46 | 35 | **35** |
| Winner in Pool率 | 0.947368 | **0.961404** |

### 4.2 変更禁止境界（維持）

Prediction API / PI API / Race Catalog / Web / Delete Boundary — Version 2 Accuracy でも非変更。

---

## 5. Version 3 へ持ち越す課題

V2 で残ったギャップは、**現行 Feature（28）＋既存 Pipeline の範囲では改善限界**に近い。

### 5.1 Evaluation不足（Layer3）

| 内容 | 詳細 |
|------|------|
| 代表 | G1 遠位 2 件（surv≪N+2：ウィリアムバローズ / スズカコテキタイ） |
| V2 結果 | CE-V2-A（温度）は悪化。CE-V2-C は未実施・V2 終了により持ち越し |
| V3 示唆 | 較正だけでは足りない可能性。学習・表現の見直しは **新 Feature Contract 前提**になりうる |

### 5.2 境界不足（Layer2 近傍）

| 内容 | 詳細 |
|------|------|
| 代表 | G1 境界 4 件（surv≈N+2） |
| V2 結果 | RP-NEAR は Rescue 0。帯緩和机上でも deep victim 不足 |
| V3 示唆 | **新 Rescue / Selection Trigger**（並べ替え専用 RO 等）の設計が必要。RP-V2-A の再利用は非推奨 |

### 5.3 新 Trigger

| 内容 | 詳細 |
|------|------|
| 並べ替え型 4 件 | surv≤N なのに selected 外（compress 副作用） |
| V2 | RO-V2 は設計のみ・未実装 |
| V3 | 「Pool 内並べ替え」専用 Trigger を Accuracy から切り離して再設計 |

### 5.4 新 Feature を使わない範囲の限界

| 観測 | 含意 |
|------|------|
| PE のみ +2 Hit | Pool 入場の局所改善は効いた |
| RP / CE-A FAIL | 下流選定・確率温度では残 G1 を回収できず、むしろ CE は退行 |
| F01 Archive 維持 | **現行 28 Feature 固定のままでは、残 miss（特に遠位・境界・Delete 34）の大半は天井** |
| V3 | 新 Feature / 学習を検討する場合は **別 Contract + ROI Validation** が必須。V2 の Flag 継ぎ足しでは足りない |

### 5.5 対象外のまま（V3 でも原則）

- Delete Boundary（rank46 after_delete ≈34）
- G1 allowlist / 勝者リーク型トリガ
- RP-V2-A パラメータ再挑戦

---

## 6. 結論

1. **Version 2 Accuracy 検証は終了**する。  
2. **最終採用は PE-V2-A のみ。** Hit **218** が V2 Accuracy の成果。  
3. RP-V2-A / CE-V2-A は **不採用**（Flag OFF）。  
4. 残課題（Evaluation / 境界 / 新 Trigger / Feature 限界）は **Version 3 Roadmap** へ引き継ぐ。

---

## 7. 参照

| 文書 | パス |
|------|------|
| Experiment Summary CSV | `compare/v2_accuracy_experiment_summary.csv` |
| V3 Roadmap Update | `docs/releases/v2-accuracy-v3-roadmap.md` |
| Accuracy 設計（V2.2） | `docs/releases/v2-accuracy-design-review.md` |
| G1 層分類 | `compare/v2_accuracy_g1_layer_classification.csv` |
| G1 FAIL 観測 | `docs/ops/v2-rp-v2-a-g1-fail-observation.md` |
| CE-V2 設計 | `docs/releases/v2-ce-v2-design-review.md` |
