# Version75 — World Strategy Design

**Date:** 2026-07-28  
**Status:** Design Specification ONLY — **実装禁止 / PE 変更禁止**  
**Parents:** V74 World Strategy Validation（Verdict B） / V43 Semantic / V72–V73 CEW  
**Corpus 根拠:** 285R CEW ラベル（V74 `_v74-world-strategy-validation.json`）  
**非目的:** Hit 改善・Prediction 変更・Trigger/Blueprint 変更

---

## 設計原則

1. World は **Strategy Selector**（何を読むかの切替）であり、単一特徴の加点表ではない（V74）。  
2. Goal は **V43 Semantic**、優先特徴・相互作用は **V74 実測**を主根拠とする。  
3. n\<20 の World は **仮説 Strategy**（PE Ready にしない）。  
4. 馬特徴の勝ち極性は World 間で概ね共通（win_prob↑ / history↑ / odds↓）。差は **優先順位・文脈相互作用・脚質**に置く（V74）。

---

## ① World Goal / ② Strategy（World 別）

### `rank7_world`（n=65・安定）

| 項目 | 定義 |
|---|---|
| **Goal** | 展開・混戦が能力評価以上に効くレースで、**能力一本勝ちを過信せず**、履歴・市場・相対能力をバランスして読む（V43 rank7 Purpose）。 |
| **優先特徴** | 1 `history_z` (effect 0.707) → 2 `win_prob_z` (0.690) → 3 `odds_z` (0.681)（V74）。三者は接近。 |
| **組み合わせ** | `history` と `win_prob` を **同格バンドル**として読み、単一 Top1 能力に閉じない。`odds` を第三軸（FieldHit 最高 0.308）。 |
| **文脈** | `field_size ↑` ほど勝ち馬の `win_prob_pct` が下がる（r=**−0.113**）。多頭では本命度を減衰。`upper_ability_band ↑` では勝ち馬 win_prob_pct が上がる（r=+0.258）。 |
| **脚質** | 逃げ (+0.097) / 先行 (+0.077) が正リフト。差し・追込は負。 |
| **読まないこと** | midhole と同じ「history だけ突出・win_prob 弱い」前提。rank7 では win_prob もほぼ同格。 |

### `midhole_world`（n=24・安定）

| 項目 | 定義 |
|---|---|
| **Goal** | 中位帯が開いたレースで、**上位能力一本を相対的に弱め**、履歴・中位候補を重視する（V43 midhole）。 |
| **優先特徴** | 1 `history_z` (0.707) → 2 `odds_z` (0.519) → 3 `win_prob_z` (**0.287・弱い**)。FieldHit(win_prob) は **0.083** のみ。 |
| **組み合わせ** | **history 主導** + odds 補助。win_prob は第三・減衰。 |
| **文脈** | `field_size ↑` → winner win_prob_pct **正**（r=+0.159）※rank7 と符号逆転。`upper_ability_band ↑` → winner win_prob_pct **負**（r=−0.234）※rank7 と逆転。`top_gap ↑` → history_pct 正（+0.208）。 |
| **脚質** | 先行 (+0.095) が首位。差しはほぼ中立 (+0.008)。 |
| **読まないこと** | win_prob Top1 を主軸にする（本 World では効果が薄い）。 |

### `unsatisfied`（n=176・安定・残余ラベル）

| 項目 | 定義 |
|---|---|
| **Goal** | CEW 上どの Positive World も MATCH しないレースの **残余扱い**。独自勝ち筋の主張はしない（V44 unsatisfied）。 |
| **優先特徴** | 1 `popularity_z` (1.063*) → 2 `win_prob_z` (0.831) → 3 `odds_z` (0.691)。\*popularity は変動あり部分集合。 |
| **組み合わせ** | 市場・能力の **汎用ベースライン**（World 固有 Selector ではない）。 |
| **文脈** | top_gap 平均 0.040（MATCH Worlds より高め）。field_size×win_prob_pct は正（+0.145）。 |
| **脚質** | 逃げ (+0.119)。 |
| **読まないこと** | unsatisfied を「第7の勝ち筋 World」として PE 特殊戦略化すること（契約上は未充足）。 |

### `core_world`（n=8・不安定 → 仮説）

| 項目 | 定義 |
|---|---|
| **Goal（V43）** | 能力決着。Gap/分離に沿って上位が勝ち切る。 |
| **優先特徴（V74 仮）** | win_prob_z ≫ odds_z ≫ history_z。先行リフト大 (+0.337)。top_gap 平均 **0.050**（全 World 中最高帯）。 |
| **制約** | n=8 のため **確定 Strategy ではない**。V43 Goal は維持、優先順位は要再測。 |

### `midupper_world`（n=6・不安定 → 仮説）

| 項目 | 定義 |
|---|---|
| **Goal（V43）** | 上位能力帯 + 展開 + 適性。 |
| **優先特徴（V74 仮）** | win_prob ≈ odds ≈ history（三者接近）。差しリフト +0.201。ability_subordinate 高め (0.90)。 |
| **制約** | n=6。適性軸の馬特徴は本コーパス列に無く、V74 では未測。 |

### `mixed_world`（n=6・不安定 → 仮説）

| 項目 | 定義 |
|---|---|
| **Goal（V43）** | 複数勝ち筋共存。単一方針に閉じない。 |
| **優先特徴（V74 仮）** | win_prob_z 極大、**history ほぼ無効**（effect ≈ 0）。追込リフト +0.175。 |
| **制約** | n=6。multi_path の「複数 Strategy の合成」は設計上必須だが、合成重みは未確定。 |

### `bug_world`（n=0）

| 項目 | 定義 |
|---|---|
| **Goal（V43）** | 例外・説明不能。 |
| **Strategy** | **定義不能**（285R CEW に標本なし）。exception 標識前提の特殊扱いのみ文書化可能。 |

---

## ④ Separation（差分表）

| 対比 | 差の実測根拠（V74） |
|---|---|
| midhole vs rank7 | win_prob 効果: midhole 弱 / rank7 強。脚質: 先行 vs 逃げ。**field_size×win_prob_pct 符号逆転**。**upper_ability_band×win_prob_pct 符号逆転**。 |
| rank7 vs unsatisfied | unsatisfied は popularity 首位・top_gap 高め。rank7 は history 首位級・混沌寄り MATCH。 |
| midhole vs unsatisfied | midhole は mid_band 開き + history 主導。unsatisfied は市場・能力ベースライン。 |
| core（仮）vs midhole | core は top_gap 高・win_prob 首位。midhole は top_gap 低・history 首位。 |
| midupper/mixed/bug | 標本不足 — Separation 未証明（V74）。 |

---

## Strategy 一覧（一文）

| World | Strategy 一文 |
|---|---|
| rank7 | 履歴・能力・オッズを同格に読み、多頭では本命度を減衰する |
| midhole | 履歴主導、能力一本を弱め、上位帯拡大時は本命度をさらに減衰 |
| unsatisfied | 市場＋能力の汎用ベースライン（勝ち筋主張なし） |
| core | （仮説）能力・短オッズ・先行寄り |
| midupper | （仮説）能力＋市場＋履歴の均衡、差し余地 |
| mixed | （仮説）能力寄りだが履歴無効 — 単一軸禁止の合成が必要 |
| bug | 未定義（標本ゼロ） |

---

## 関連

- `v75-world-strategy-contract.md` — 評価ポリシー契約  
- `v75-world-readiness.md` — PE 成熟度  
- `v75-governance.md`
