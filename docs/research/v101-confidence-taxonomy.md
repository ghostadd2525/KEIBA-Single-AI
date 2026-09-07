# Version101 — Confidence Taxonomy

**Date:** 2026-07-28  
**Status:** Taxonomy（定義）· **実装禁止**  
**ADR:** ADR-010

---

## 総称

**Explanation Confidence（EC）** — Core が扱う唯一の Confidence 族。

---

## 軸一覧

| Code | Name | 問い | 主入力 |
|---|---|---|---|
| **EC-S** | Semantic Confidence | なぜこの World / 残余なのか説明できるか | why-parts / Expected Strategy |
| **EC-W** | World Confidence | World ラベルと契約トレースは確定しているか | CEW + decision_trace + strategy map |
| **EC-N** | Near Miss Confidence | unsatisfied の近接記述は確定しているか | Taxonomy + Affinity + gaps + excl |
| **EC-T** | Trace Confidence | Must / Exclusion / Match / Path は足りるか | decision_trace + trigger_path + transition |

---

## 非 Taxonomy（明示的に除外）

| 名称（呼ばれがち） | 扱い |
|---|---|
| Prediction Confidence | **除外** — Core 非返却 |
| Win Probability Confidence | **除外** — Score 側 |
| Odds Confidence | **除外** — 市場 |
| Calibration Confidence | **除外** — Calibration / Decision 表示は別 |
| Betting Confidence | **除外** — Decision（ADR-008） |

---

## レース種別と適用

| CEW | EC-S | EC-W | EC-N | EC-T |
|---|---|---|---|---|
| Positive World | ✓ | ✓ | null | ✓ |
| unsatisfied / Near Miss | ✓ | ✓ | ✓ | ✓ |
| unsatisfied / Pure Residual | ✓ | ✓ | ✓（pure として確定） | ✓ |

---

## 確定性の段階（語彙）

数値スケール導入前の質的語彙:

| Level | 意味 |
|---|---|
| **DETERMINATE** | Must/Exclusion/Match が矛盾なく揃い、説明が閉じている |
| **PARTIAL** | 主要トレースはあるが一部ギャップ（例: exclusion reason 弱い） |
| **INDETERMINATE** | ラベルまたはトレース欠落・論理矛盾 |

Explanation Confidence の数値化は Level の連続化であり、勝率化ではない。

---

## Shadow Observation（V100 再写像・参考）

V100 Completeness 集計を EC 軸へ写像した観測（製品非実装）:

| EC 軸 | V100 対応観測 | 285R 参考値 |
|---|---|---:|
| EC-S | semantic_complete_rate | 1.000 |
| EC-W | world_complete | 1.000 |
| EC-N | near_miss_complete（unsatisfied） | 1.000 |
| EC-T | must/exclusion/match/decision_tree/transition | 1.000 |
| （参考）Prediction conf coverage | **Core KPI 外** | 0.000 |

→ 現状コーパスでは **Explanation Confidence 族は高い**。  
V100 で目立った「confidence 欠落」は **Prediction Confidence 非返却** と整合し、Core 失敗ではない。

---

## 関連

- ADR-010
- `v101-confidence-contract.md`
- `v100-core-completeness-report.md`
