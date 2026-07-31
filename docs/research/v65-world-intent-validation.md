# Version65 — World Intent Validation

**Date:** 2026-07-28  
**Subject:** 設計意図上の本来 World vs AI 付与 World（285R）  
**Locks:** PE / Prediction / Trigger / Signal / World / Threshold / Production — **変更・実装禁止**  
**禁止:** Strategy 分析 / PE 分析

---

## 結論（1行）

Production AI（Legacy World）と設計意図 GT の一致率は **22.1%**。core の過剰割当（意図外 core **84**）は V42 DEFAULT 構造と一致し、**設計意図を満たしていない（C）**。

---

## ① Ground Truth Definition（設計意図）

### 根拠

| 文書 | 用いる内容 |
|---|---|
| **V42** | 設計正本: core=能力決着（DEFAULT 残余ではない）; rank7=低 TopGap・混戦; World 意味表 |
| **V43** | Expected Characteristics / Winning Pattern（意味契約正本） |
| **V44** | 極性語彙（高/低）。**Logic Form 出力は GT にしない**（循環回避） |
| **V45** | Spec vs Production 乖離の文脈（GT ラベル自体には使わない） |

### 操作的判定（285R）

観測極性 = コーパス batch median（製品 Threshold ではない）。

| Intent World | 設計意図（要約） | 285R 判定 |
|---|---|---|
| core | 能力差・TopGap 大で上位が勝ち切る | `top_gap`≥med ∧ `ability_separation`≥med ∧ winner_rank≤3（弱条件あり） |
| midupper | 上位能力帯・core/rank7 の中間 | winner_rank 2–6、極端低 gap ではない |
| midhole | 中位評価帯が開く | winner_rank 5–10 ∧ `mid_eval_band_open`≥med |
| rank7 | 低 TopGap・能力どおりになりにくい | `top_gap`≤med ∧ winner_rank 7–10 |
| mixed | 複数勝ち筋が同時妥当 | 強適合（1.0）が 2 World 以上 |
| bug | 既存枠に乗らない深穴 | winner_rank ≥11 |
| unsatisfied | 意図が弱い | 全 score < 0.5 |

Primary 解決: 単一強適合 → それ。複数強適合 ∧ mixed → mixed。他は優先度 `bug>midhole>rank7>core>midupper>mixed`。

---

## ② Race Classification（Intent GT 分布）

| World | n | share |
|---|---:|---:|
| midupper | 92 | 32.3% |
| midhole | 50 | 17.5% |
| core | 45 | 15.8% |
| mixed | 40 | 14.0% |
| unsatisfied | 26 | 9.1% |
| bug | 25 | 8.8% |
| rank7 | 7 | 2.5% |
| **合計** | **285** | 100% |

---

## ③ AI Classification

**主対象 AI World = Production Legacy**（`legacy_world` / `decision_authority=legacy`）。

| AI World | n |
|---|---:|
| midupper | 110 |
| core | 104 |
| mixed | 56 |
| midhole | 15 |
| rank7 / bug / unsatisfied | **0** |

対照: V44 Shadow（`v44_world`）— unsatisfied 176 等。主判定には使わない。

---

## ④ Agreement

| 比較 | 一致率 |
|---|---:|
| **AI (Legacy) vs Intent GT** | **22.1%** (63/285) |
| Shadow vs Intent GT（対照） | 8.8% |

---

## 設計シェア vs AI

| World | Design | Intent GT | AI Legacy |
|---|---:|---:|---:|
| core | 30% | 15.8% | **36.5%** |
| midupper | 35% | 32.3% | 38.6% |
| rank7 | 15% | 2.5% | **0%** |
| mixed | 10% | 14.0% | 19.6% |
| bug | 5% | 8.8% | **0%** |
| midhole | 5% | 17.5% | 5.3% |

---

## 数値正本

`docs/research/_v65-intent-validation.json`
