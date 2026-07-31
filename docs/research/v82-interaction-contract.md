# Version82 — Interaction Contract

**Date:** 2026-07-28  
**Type:** Policy Contract（設計文書）  
**Authority:** V81 Interaction 測定 + V43 Semantic Goal + V80（単体 Weight 失敗）  
**実装・PE・Production・Trigger・Blueprint — 変更禁止**

表記:

| 語 | 意味 |
|---|---|
| **Must** | 当該 World の Interaction Strategy が成立するために満たすべき読み方 |
| **Aux** | Must を補強する Interaction。Must 欠落時に Must の代替にはならない（Fallback 表に別記） |
| **Forbidden** | 当該 World で採用してはならない読み方・単位 |
| **EVIDENCE** | V81（主）/ V74・V80（補助） |

---

## 共通契約（全対象 World）

| ID | 規則 |
|---|---|
| IC0 | Strategy の基本単位は **Feature Interaction**（2-way / 3-way）である。 |
| IC1 | **単体 Feature Weight** を Strategy 本体・加点表・Must として定義してはならない。 |
| IC2 | 原子特徴は Interaction の構成要素としてのみ言及する。 |
| IC3 | 同一 Interaction 文字列でも World 間で Role（Must/Aux/Forbidden）が異なり得る。 |
| IC4 | n\<20 の World Contract は **PROVISIONAL**（`core_world`）。 |
| IC5 | Hit / Purchase を本 Contract の適合判定に使わない。 |
| IC6 | Trigger / Blueprint / CEW 規則は変更しない（入力前提）。 |
| IC7 | PE / Production への写像を本 Contract は要求しない・許可しない（本フェーズ）。 |

---

## `rank7_world` Interaction Contract

**Status:** ACTIVE（n=65）  
**Semantic Goal（参照・非変更）:** 展開・混戦で能力一本を過信しない。

### Must

| ID | Interaction | 読み方 |
|---|---|---|
| R7-M1 | `history × win_prob` | 履歴と能力を **同格バンド Interaction** として読む。片方だけの主軸化をしない。 |
| R7-M2 | `history × odds × win_prob` | 上記バンドに市場を加えた **三重強化**を Must 強化層とする（2-way 欠落時の意味は Priority 参照）。 |

### Aux

| ID | Interaction | 読み方 |
|---|---|---|
| R7-A1 | `odds × ability_sep` | 市場×能力分離の補助。 |
| R7-A2 | `history × odds` | 履歴×市場の補助。 |
| R7-A3 | `win_prob × odds` | 能力×市場の補助（単体 win_prob / 単体 odds ではない）。 |
| R7-A4 | `odds × upper_band` | 上位帯×市場の補助。 |
| R7-A5 | `history × upper_band × odds` | 上位帯文脈の三重補助。 |

### Forbidden

| ID | 禁止内容 |
|---|---|
| R7-F1 | 単体 `history` / `win_prob` / `odds` Weight を Strategy Must とすること。 |
| R7-F2 | midhole の Must（`win_prob × field_size` 主ゲート）を rank7 Must に転用すること。 |
| R7-F3 | `win_prob × field_size` を rank7 の **主 Interaction** として主張すること（V81 Lift 弱）。 |
| R7-F4 | 「能力一本勝ち」Interaction 欠落（`history` 側を捨てた `win_prob` 単独相当）を許容すること。 |

### EVIDENCE
V81 rank7 Champion=`history×win_prob`; 3-way Lift≈1.84=`history×odds×win_prob`; V80 単体 Weight 失敗。

---

## `midhole_world` Interaction Contract

**Status:** ACTIVE（n=24・標本 Partial 注意）  
**Semantic Goal（参照）:** 中位帯開放で上位能力一本を相対弱め、履歴・文脈を読む。

### Must

| ID | Interaction | 読み方 |
|---|---|---|
| MH-M1 | `win_prob × field_size` | 頭数文脈で能力寄与を **ゲートする**主 Interaction（rank7 と Role が異なる）。 |
| MH-M2 | `history × pace` | 展開×履歴を Must。履歴を単体加点に落とさない。 |

### Aux

| ID | Interaction | 読み方 |
|---|---|---|
| MH-A1 | `history × field_size` | 頭数×履歴の準強化。 |
| MH-A2 | `win_prob × field_size × pace` | 主ゲートの pace 強化。 |
| MH-A3 | `history × field_size × top_gap` | ギャップ文脈の三重。 |
| MH-A4 | `history × odds × win_prob` | 汎用三重。World 固有 Must には昇格しない。 |

### Forbidden

| ID | 禁止内容 |
|---|---|
| MH-F1 | rank7 の `history × win_prob` **同格 Must** をそのままコピーすること。 |
| MH-F2 | `win_prob` 単体主軸 / 単体 Weight。 |
| MH-F3 | `win_prob × upper_band` を強化方向の Must とすること（V81 Lift 低・V74 減衰側）。 |
| MH-F4 | field_size ゲート無しで rank7 三重を midhole 主戦略とすること。 |

### EVIDENCE
V81 midhole Champion=`win_prob×field_size`; `history×pace` Lift 1.33; V74 midhole↔rank7 符号差。

---

## `unsatisfied` Interaction Contract

**Status:** ACTIVE（n=176・Residual Policy）  
**Semantic Goal（参照）:** Positive World 未充足の残余。独自勝ち筋を主張しない。

### Must

| ID | Interaction | 読み方 |
|---|---|---|
| US-M1 | `history × win_prob` | **Baseline Interaction** として読む。World 固有勝ち筋の証明ではない。 |

### Aux

| ID | Interaction | 読み方 |
|---|---|---|
| US-A1 | `win_prob × odds` | 市場×能力ベースライン補助。 |
| US-A2 | `history × odds` | 履歴×市場補助。 |
| US-A3 | `win_prob × field_size` | 頭数文脈補助（midhole Must への昇格禁止）。 |
| US-A4 | `history × win_prob × odds` | ベースライン三重強化。 |
| US-A5 | `win_prob × field_size × pace` | 展開×頭数補助。 |

### Forbidden

| ID | 禁止内容 |
|---|---|
| US-F1 | unsatisfied を「第7の勝ち筋 World」として固有 Must セットを肥大化させること。 |
| US-F2 | rank7 / midhole の World 固有 Must を unsatisfied Must に転用すること。 |
| US-F3 | 単体 Feature Weight Strategy。 |
| US-F4 | Residual ラベルを PE 特殊戦略の根拠にすること（本フェーズ・設計上も非推奨継続）。 |

### EVIDENCE
V81 unsatisfied Champion=`history×win_prob`; 3-way Lift≈1.95; V44/V75 Residual 契約。

---

## `core_world` Interaction Contract

**Status:** PROVISIONAL（n=8）  
**Semantic Goal（参照）:** 能力決着（V43）。測定は不安定。

### Must（仮）

| ID | Interaction | 読み方 |
|---|---|---|
| CR-M1 | `win_prob × odds` | 能力×市場を仮の主 Interaction とする。 |

### Aux（仮）

| ID | Interaction | 読み方 |
|---|---|---|
| CR-A1 | `history × win_prob` | 仮補助（標本敏感）。 |
| CR-A2 | `history × odds × win_prob` | 仮三重。 |
| CR-A3 | `win_prob × field_size × top_gap` | Gap 文脈仮説。 |

### Forbidden

| ID | 禁止内容 |
|---|---|
| CR-F1 | 本 Contract を ACTIVE / Ready / Pilot Must と主張すること。 |
| CR-F2 | 単体 Weight または他 World Must の無条件転用。 |
| CR-F3 | n=8 の Lift 極大値を確定証拠として扱うこと。 |

### EVIDENCE
V81 core Champion=`win_prob×odds`; n=8 → PROVISIONAL。

---

## 適合チェック（設計レビュー用・非実装）

World を1つ選んだとき:

1. Must Interaction が列挙されているか（単体になっていないか）  
2. Forbidden に単体 Weight と他 World Must 転用が含まれるか  
3. `core` が PROVISIONAL のままか  
4. PE/Trigger/Blueprint への参照変更が混入していないか  
