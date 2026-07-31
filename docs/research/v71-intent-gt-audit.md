# Version71 — Intent Ground Truth Audit

**Date:** 2026-07-28  
**Status:** Research / Audit only — **Trigger 変更禁止・実装禁止**  
**Parents:** V70 W-S4 Shadow（Gate FAIL: Intent Accuracy 0.221→0.088） / V65 Intent Validation / V43–V44–V69  
**Locks:** Trigger / Threshold / Polarity / PE / Prediction / Production — 不変  
**Evidence:** V65 `_v65-intent-validation.json` 生成規則 + V70 285R Dual rows（参照のみ）

---

## 結論（1行）

Intent GT（V65）は **V43 Semantic / V44 Trigger Spec / V69 Blueprint と同一定義ではない**。  
主に **事後 winner_model_rank ヒューリスティック**であり、V43 Required Signals / V44 Must Logic Form を満たしていない。  
V70 の Intent Accuracy 低下は **Blueprint 失敗の証拠ではなく、GT と Positive Match の軸ずれの再測定**である（V65 時点で Shadow↔Intent は既に **8.8%**）。

---

## 調査対象 4 者

| ID | 文書 / 実装 | 役割 |
|---|---|---|
| ① | `docs/architecture/v43-world-semantic-contract.md` | World 意味（勝ち筋）正本 |
| ② | `docs/architecture/v44-world-trigger-specification.md` + `v44-trigger-logic.md` | Must/Aux/Forbidden + Logic Form |
| ③ | `docs/implementation/v69-trigger-refactoring-design.md` | R7/R1/R8 + Decision Tree Blueprint |
| ④ | `_v65_world_intent_validation.py` → Intent GT | V70 Gate の参照 GT |

---

## ① Ground Truth 生成規則（現行・事実）

Authority 自己宣言（V65）: V42 正本 + V43 Expected Characteristics + V44 **極性語彙のみ**。  
明示: **「V44 Logic Form 出力は GT にしない（循環回避）」**。

### 操作的スコア（`intent_scores`）

観測極性 = 285R batch median（製品 Threshold ではない）。入力は主に:

- ranking concepts: `top_gap`, `ability_separation`, `mid_eval_band_open`
- **`winner_model_rank`（事後結果）**

| Intent World | score=1.0 条件（要約） | score=0.5 等 |
|---|---|---|
| core | gap↑ ∧ sep↑ ∧ **wr≤3** | gap↑∧wr≤3 (0.75); gap↑∧wr≤5 (0.5) |
| midupper | **wr∈[2,6]** ∧ ¬gap↓ | wr∈[2,6] のみ (0.5); gap↑∧wr≤2 は 0.5 |
| midhole | **wr∈[5,10]** ∧ mid_band↑ | wr∈[5,10] のみ (0.5) |
| rank7 | gap↓ ∧ **wr∈[7,10]** | gap↓∧wr∈[6,11] / wr∈[7,10] (0.5) |
| bug | **wr≥11** | wr≥9 (0.5) |
| mixed | 強適合(1.0) World が **2+** | 弱適合(0.5) が 3+ |
| unsatisfied | （pick 時）全 score < 0.5 | — |

### ラベル解決（`pick_intent_gt`）

1. 強適合が 1 → その World  
2. 強適合が 2+ かつ mixed=1.0 → mixed  
3. 強適合が 2+ → 優先度 `bug > midhole > rank7 > core > midupper > mixed`  
4. 最大 score < 0.5 → unsatisfied  
5. それ以外 → 最良 score（同点は上記優先度）

### 285R 付与結果（V65 / V70 同一規則）

| World | n | share | winner_rank 中央（V70 rows） |
|---|---:|---:|---:|
| midupper | 92 | 32.3% | 4（範囲 2–6） |
| midhole | 50 | 17.5% | 6（5–10） |
| core | 45 | 15.8% | 1（1–3） |
| mixed | 40 | 14.0% | 6（3–10） |
| unsatisfied | 26 | 9.1% | 1（1–1） |
| bug | 25 | 8.8% | 12（9–15） |
| rank7 | 7 | 2.5% | 8（7–10） |

**観測事実:** Intent ラベルは World ごとに **winner_rank 帯と強く共変**している（上記中央値）。

---

## ② Blueprint / Spec との差分（定義レイヤ）

| 観点 | V43 Semantic | V44 Trigger Spec | V69 Blueprint | Intent GT（V65） |
|---|---|---|---|---|
| World の性質 | **勝ち筋（事前意味）** | **Positive Match（Signal Logic）** | V44 の実装可能形 | **事後 winner_rank 帯 + 一部 concept** |
| core | 能力決着の独立勝ち筋 | Gap↑∧Sep↑ ∧ NOT Exclude | 同左 / DEFAULT 廃止 | Gap↑∧Sep↑ **∧ wr≤3** |
| midupper | UPPER ∧ 展開 ∧ **適性** | UPPER∧DEV∧APT | 同左（difficulty Aux） | **ほぼ wr∈[2,6] のみ**（適性・DEV なし） |
| midhole | 中位帯開き ∧ 上位独占弱 | MidOpen∧WeakMono | （V44 Form 維持） | wr∈[5,10]（± mid_open） |
| rank7 | chaos ∧ 展開圧 ∧ 能力劣後 | Chaos∧Pace∧Subordinate | （V44 Form 維持） | gap↓ ∧ wr∈[7,10]（**chaos なし**） |
| mixed | 複数勝ち筋共存 | multi_path / unexplained | multi_path MATCH | スコア強適合の 2+（outcome 由来） |
| bug | 例外標識 | ExceptionFlag Must | Exception 欠落⇒不成立 | **wr≥11**（例外 Signal なし） |
| 残余 | （意味上は未分類可） | **unsatisfied**（DEFAULT 禁止） | \|M\|=0 → unsatisfied | score 全弱 → unsatisfied |
| 評価対象 | 意味契約 | Trigger 設計 | Shadow Logic Form | 「設計意図」と自称するが Logic Form 非準拠 |

---

## ③ Intent Label 付与規則の問題分類

| ID | 問題 | 根拠 |
|---|---|---|
| IG-1 | **Outcome-as-World** | V43 G1: World=勝ち筋。Intent GT は winner_model_rank を Must 相当に使用。勝ち筋（事前）≠結果帯（事後）。 |
| IG-2 | **Expected Characteristics の誤用** | V43 §⑥ / V44 T1: Expected Characteristics は「成立時の検証観点」。GT 本体にしていない（V44）。V65 はこれを操作的 GT の主軸にした。 |
| IG-3 | **Required / Must Signal 欠落** | midupper から aptitude・DEV 欠落; rank7 から chaos・pace 欠落; bug から exception 欠落。 |
| IG-4 | **循環回避の副作用** | V65 は Logic Form を GT にしないと明記 → Blueprint（V69）成功条件と GT が構造的に非整合。 |
| IG-5 | **Design share 乖離** | rank7 Design 15% vs Intent GT **2.5%**（7/285）。chaos Must を入れないため support が極小。 |
| IG-6 | **Winner Alignment との混同** | V70 の `winner_alignment_*` と同型の rank 帯ルールを Intent「意味」に流用。 |

---

## ④ 矛盾一覧（4 者マトリクス）

| # | 主張 A | 主張 B | 矛盾か |
|---|---|---|---|
| C1 | V43 midupper Required = 上位帯+展開+適性 | Intent midupper = wr 2–6 | **Yes** — 適性/展開 Must 欠落 |
| C2 | V44/V69 midupper Forbidden = difficulty のみ | Intent は difficulty を見ない（別軸） | 直接矛盾ではないが **測定非対応** |
| C3 | V43/V44 rank7 Must = chaos↑ | Intent rank7 = gap↓∧wr 7–10 | **Yes** — chaos 不在 |
| C4 | V43/V44 bug Must = 例外標識 | Intent bug = wr≥11 | **Yes** — 深穴結果 ≠ exception |
| C5 | V44 T0 Positive Match / unsatisfied 正当 | Intent Accuracy は unsatisfied を「外れ」扱い | **測定定義矛盾** — Blueprint 成功（DEFAULT 除去）が Accuracy を下げうる |
| C6 | V69 Decision \|M\|=0 → unsatisfied | Intent は midupper/core を outcome で大量付与 | **Yes** — V70 不一致 Top: midupper→unsatisfied 52, core→unsatisfied 42 |
| C7 | V65「Shadow vs Intent = 8.8%」 | V70 V69 vs Intent = 8.8% | **矛盾なし** — 同一 GT に対する Positive Match 系の再測定 |
| C8 | V70 PASS「Intent Accuracy 改善」 | GT が V69 と非整合 | **Gate 前提欠陥** — 改善不能な比較軸 |

---

## ⑤ どこで乖離したか（時系列）

```text
V43 Semantic Contract
  │  World = 勝ち筋 / Required Signals / Forbidden
  ▼
V44 Trigger Spec
  │  Must Logic Form / Positive Match / unsatisfied
  │  Expected Characteristics = 検証観点（GT ではない）
  ▼
V65 Intent Validation  ← ★乖離点
  │  「循環回避」で Logic Form を除外
  │  Expected Characteristics + winner_rank を操作的 GT 化
  │  → Outcome-band GT が固定される
  ▼
V69 Blueprint / V70 Shadow
     V44 整合の Positive Match を実装・評価
     → Intent Accuracy 低下は GT 軸ずれの露出
     （構造 KPI: rank7 Recall↑ / DEFAULT=0 は Blueprint どおり）
```

**乖離の本体:** V65 が「意図 GT」を **V43 Required / V44 Must ではなく、事後 rank 帯**に置いたこと。

---

## ⑥ V70 Accuracy 低下の監査解釈（推測禁止・対応表のみ）

| V70 観測 | GT 監査上の読み |
|---|---|
| Intent Acc 0.221→0.088 | Legacy は midupper/core 過剰で outcome 帯と偶発一致しやすい。V69 は Positive Match → unsatisfied 増で outcome GT と不一致増。 |
| V65 Shadow↔Intent 既に 8.8% | V70 は新規悪化ではなく **同型測定の再現**。 |
| rank7 Recall 0→0.857 (6/7) | GT rank7 が 7 件のみ（outcome 定義）。V69 の chaos Form が当該 7 に当たりやすい一方、GT 外の rank7 MATCH（65）は「偽陽性」扱いになる。 |
| DEFAULT 104→0 | V43/V44/V69 と **整合**。Intent GT は DEFAULT 概念を持たないため Accuracy に正の寄与を与えない。 |

---

## 非範囲

- Trigger / V69 実装の改修  
- Intent GT の再定義・再スコアリング実装  
- PASS 再判定のための Gate 書き換え実装  

本 Audit は **GT 妥当性の文書化**まで。

---

## 関連成果物

| Doc | Content |
|---|---|
| `v71-intent-gt-audit.md` | 本ファイル |
| `v71-intent-mapping.md` | World 別 4 者マッピング |
| `v71-blueprint-consistency.md` | V69↔GT 一貫性判定 |
| `v71-governance.md` | 統治 |
