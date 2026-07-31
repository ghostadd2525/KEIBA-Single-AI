# Version64 — World Classification Validation

**Date:** 2026-07-28  
**Subject:** World 分類が V43/V44 設計意図どおりか（285R）  
**Locks:** PE / Prediction / Trigger / Signal / Threshold / World Logic / Production — **変更・実装禁止**  
**Scope:** PE 研究禁止 / Strategy 研究禁止（本検証 PASS 後に再開）

---

## 結論（1行）

Shadow World は 285R で **unsatisfied 61.8%**、V43 意味 GT との一致率 **9.5%**、WA aligned **11.2%**。V44 Positive Match 原則を満たしておらず、**World 分類は設計意図を満たしていない（Governance C）**。

---

## ① World Ground Truth 定義

### 根拠文書

| 層 | 文書 | 役割 |
|---|---|---|
| 意味 | V43 World Semantic Contract | Purpose / Winning Pattern / Expected Characteristics |
| Trigger 仕様 | V44 World Trigger Specification / Signal Roles / Logic Form | Must / Aux / Forbidden / Positive Match |
| 乖離監査 | V45 World Compliance | Production ≠ Spec の既証 |

### GT の定義方針（循環回避）

V44 Logic Form の **Shadow 出力そのものを GT にしない**（一致率 100% の同語反復になる）。

本フェーズの **Ground Truth = V43 Expected Characteristics を 285R 観測量へ写像した Semantic Oracle**:

| World | 「このレースは当該 World」とみなす設計基準（V43） | 285R への操作的写像 |
|---|---|---|
| **core** | 能力差・TopGap 大、上位能力が勝ち切る | `top_gap`≥batch median **かつ** winner `model_rank`≤3（弱: ≤5） |
| **midupper** | 上位能力帯・展開影響、core/rank7 の中間 | winner rank 2–6、極端な低 gap 経路ではない |
| **midhole** | 中位評価帯が開く | winner rank 5–10 **かつ** `mid_eval_band_open`≥median |
| **rank7** | 低 TopGap・混戦、能力どおりになりにくい | `top_gap`≤median **かつ** winner rank 7–10 |
| **mixed** | 複数勝ち筋が同時に妥当 | 強適合（score=1.0）が **2 World 以上** |
| **bug** | 既存枠に乗らない深穴・例外 | winner rank ≥11 |
| **unsatisfied** | いずれの Expected Characteristics も弱い | 全 score < 0.5 |

極性の「高/低」は V44 T3 に合わせ **285R batch median**（閾値の製品固定ではない・観測的極性）。

**Primary GT:** 強適合が1つならそれ。2つ以上かつ mixed=1.0 なら mixed。それ以外は仕様優先度 `bug > midhole > rank7 > core > midupper > mixed`。

### 予測側（検証対象）

| 系 | ラベル源 | 役割 |
|---|---|---|
| **Shadow（主）** | dual-eval `v44_world` | 現行 V44 Shadow 分類 |
| Legacy（対照） | `legacy_world` | Production Trigger（参考・変更なし） |

---

## ② World Classification Accuracy

| 比較 | Accuracy | n |
|---|---:|---:|
| **Shadow vs Semantic GT** | **9.5%** (27/285) | 285 |
| Legacy vs Semantic GT | 22.5% | 285 |
| Shadow 契約自己整合（割当∈match_set） | **100%** | 285 |

自己整合 100% は「Shadow 実装が自分の Logic Form と矛盾しない」ことのみを示す。  
**設計意味 GT との一致は別問題**であり、こちらは失敗。

### 分布（設計ミックス対照）

| World | Design share | Semantic GT | Shadow | Legacy |
|---|---:|---:|---:|---:|
| core | 30% | 80 (28%) | **8 (2.8%)** | 104 |
| midupper | 35% | 54 (19%) | **6 (2.1%)** | 110 |
| midhole | 5% | 82 (29%) | 24 (8.4%) | 15 |
| rank7 | 15% | 7 (2.5%) | **65 (22.8%)** | 0 |
| mixed | 10% | 11 (3.9%) | 6 (2.1%) | 56 |
| bug | 5% | 25 (8.8%) | **0 (0%)** | 0 |
| unsatisfied | — | 26 (9.1%) | **176 (61.8%)** | 0 |

V44 T0 Positive Match: 「残余 DEFAULT 禁止・正条件で選ぶ」。Shadow の主結果が **unsatisfied 61.8%** であり、設計どおりの分類器としては不成立。

---

## ⑥ Winner Alignment（分類 ↔ 勝ち筋）

| ラベル系 | aligned | soft | misaligned | unsatisfied | aligned率 |
|---|---:|---:|---:|---:|---:|
| Shadow | 32 | 20 | 57 | 176 | **11.2%** |
| Semantic GT | （GT 定義上 aligned 寄り） | — | — | — | 69.5%* |
| Legacy | — | — | — | — | 31.6% |

\*GT aligned率は GT ラベルに対する WA 定義の結果（`_v64-classification-validation.json`）。

Shadow は大半が unsatisfied のため、**勝ち筋との一致を分類として主張できない**。

---

## 数値正本

`docs/research/_v64-classification-validation.json`

## 関連成果物

| Doc | 内容 |
|---|---|
| `v64-world-accuracy.md` | Precision / Recall |
| `v64-confusion-matrix.md` | 混同行列 |
| `v64-root-cause.md` | 誤分類原因 |
| `v64-governance.md` | 判定 |

---

## 明示的非実施

PE / Strategy / Trigger / Signal / Threshold / World Logic / Production — すべて未変更。
