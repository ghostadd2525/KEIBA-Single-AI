# Version75 — World Strategy Contract

**Date:** 2026-07-28  
**Type:** Policy Contract（設計文書）  
**Authority:** V43 Semantic（Goal） + V74 285R 測定（優先特徴・相互作用）  
**実装・PE・Prediction・Trigger — 変更禁止（本フェーズ）**

表記:

- **MUST** — 当該 World Strategy が主張するとき満たすべき読み方  
- **SHOULD** — 推奨  
- **MUST NOT** — 禁止（他 World の読み方の誤用）  
- **EVIDENCE** — V74 根拠（n / effect / r）

---

## 共通契約（全 World）

| ID | 規則 |
|---|---|
| C0 | Strategy は **Selector** である。単一グローバル重みの上書き定義ではない。 |
| C1 | 馬特徴の基本極性（win_prob↑ / history↑ / odds↓）は共有してよい（V74: 符号逆転なし）。 |
| C2 | World 差は **優先順位・組み合わせ・文脈ゲート・脚質** に置く。 |
| C3 | n\<20 の World は Contract を **PROVISIONAL** とし、PE 組み込み MUST にしない。 |
| C4 | Hit / Purchase を本 Contract の適合判定に使わない（本フェーズ非目的）。 |
| C5 | Trigger / CEW ラベル規則は変更しない（本 Contract の入力前提）。 |

---

## `rank7_world` Strategy Contract

**Status:** ACTIVE（n=65）

### Goal
展開・混戦優位レースで、能力一本勝ちを過信しない評価。

### MUST
1. 評価時に `history` と `win_prob` を **同格優先バンド**として扱う（effect 0.707 / 0.690）。  
2. `field_size` が大きいほど、勝ち候補の **win_prob 依存を減衰**する文脈ゲートを持つ（r=−0.113）。  
3. 差し・追込を主勝ち脚質として主張しない（リフト負）。

### SHOULD
1. `odds` を第三軸として併用（effect 0.681, FieldHit 0.308）。  
2. `upper_ability_band` が高いときは win_prob 寄与を相対的に強めてよい（r=+0.258）。

### MUST NOT
1. midhole 用の「win_prob 大幅減衰・history 単独主導」をそのまま適用する。  
2. 多頭フィールドで win_prob Top1 を無条件強化する。

### EVIDENCE
V74 importance / style / interactions（rank7 n=65）。

---

## `midhole_world` Strategy Contract

**Status:** ACTIVE（n=24）

### Goal
中位帯開放レースで、上位能力一本を弱め履歴・中位候補を読む。

### MUST
1. `history` を第一優先とする（effect 0.707 ≫ win_prob 0.287）。  
2. `win_prob` の主軸化を行わない（FieldHit 0.083）。  
3. `upper_ability_band` 上昇時に win_prob 依存を **減衰**する（r=−0.234）。

### SHOULD
1. `odds` を第二軸（0.519）。  
2. 先行脚質を相対的に優遇してよい（lift +0.095）。  
3. `field_size` 増で win_prob 寄与を弱めすぎない（r=+0.159 — rank7 と逆）。

### MUST NOT
1. rank7 の「history≈win_prob 同格」バンドをそのまま使う。  
2. 多頭＝本命減衰（rank7 ゲート）を無条件コピーする。

### EVIDENCE
V74 midhole n=24; midhole↔rank7 符号逆転 2 件。

---

## `unsatisfied` Residual Policy Contract

**Status:** ACTIVE-RESIDUAL（n=176）  
**Note:** Positive World ではない。CEW 未充足の扱い。

### Goal
契約 MATCH なしレースに対する **汎用ベースライン**。勝ち筋の新規主張をしない。

### MUST
1. World 固有 Selector（rank7/midhole 等）を強制適用しない。  
2. 利用可能なら市場（popularity/odds）と win_prob のベースラインを用いる。

### SHOULD
1. popularity が観測可能なレースでは市場軸を優先参照（effect 1.063, 部分集合）。  
2. 逃げリフト正（+0.119）を弱い補助としてよい。

### MUST NOT
1. unsatisfied を bug や core DEFAULT と同一視する。  
2. unsatisfied 専用の「第7勝ち筋」PE 戦略を本 Contract で正当化しない。

### EVIDENCE
V74 unsatisfied n=176。

---

## `core_world` Strategy Contract

**Status:** PROVISIONAL（n=8）

### Goal（V43 固定）
能力決着の正検出に沿った評価。

### MUST（設計意図）
1. Goal を「残余 DEFAULT」にしない（V43 Forbidden）。  

### SHOULD（V74 仮・再測前提）
1. win_prob を第一候補、odds を第二。  
2. 先行脚質を相対優遇。  

### MUST NOT
1. PROVISIONAL のまま PE 本番重みを確定する。  

### EVIDENCE
V43 Goal + V74 n=8（不安定）。

---

## `midupper_world` Strategy Contract

**Status:** PROVISIONAL（n=6）

### Goal（V43 固定）
上位能力 + 展開 + 適性。

### SHOULD（仮）
win_prob / odds / history の均衡読み。差し余地の観測あり（lift +0.201）。

### MUST NOT
difficulty 単独を Strategy 本体にする（V43 Forbidden — Trigger 側と整合）。  
PE 確定重み化。

### EVIDENCE
V43 + V74 n=6。適性特徴は 285R コーパス未測。

---

## `mixed_world` Strategy Contract

**Status:** PROVISIONAL（n=6）

### Goal（V43 固定）
複数勝ち筋の共存。単一方針禁止。

### MUST（設計）
1. 単一特徴ランキングを唯一の Strategy としない。  
2. 構成 Primary Worlds の Strategy を **合成参照**する枠を持つ（重みは未定）。

### SHOULD（仮）
V74 では win_prob 強く history 無効 — 「履歴無効を混ぜる」仮説のみ。確定禁止。

### MUST NOT
phase / 圧力単軸を mixed Strategy の定義にする（V43/V44）。

### EVIDENCE
V43 + V74 n=6。

---

## `bug_world` Strategy Contract

**Status:** BLOCKED（n=0）

### Goal（V43）
例外・説明不能。

### MUST
exception 標識なしに bug Strategy を発動しない。

### MUST NOT
「どれにも非該当」を bug Strategy にする（= unsatisfied / 旧 DEFAULT 混同）。

### EVIDENCE
285R CEW 標本 0。

---

## Contract 間の排他（Separation）

| From | To | 排他内容 |
|---|---|---|
| rank7 | midhole | field_size ゲート符号 / win_prob 優先度 / 脚質（逃げ vs 先行） |
| midhole | rank7 | history 単独主導の強制を rank7 に持ち込まれない |
| any Positive | unsatisfied | Positive Selector を残余に強制しない |
| any | bug | 標本・exception なしに bug 戦略を使わない |
| core PROVISIONAL | production PE | 確定組み込み禁止 |
