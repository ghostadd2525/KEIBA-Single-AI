# Version43 — World Semantic Contract（正本）

**Date:** 2026-07-28  
**Status:** Design Contract RESTORED（設計契約の復元。実装・Trigger・Signal・Production は変更しない）  
**Type:** Research / Design only  
**Authority chain:**

| 層 | 文書 / コード | 役割 |
|---|---|---|
| 哲学 | V32 ADR / V36 | World = AI 最上流の **勝ち筋分類** |
| 入力契約 | V33 World Input Contract | Signal 層（L0–L2）の命名・必須 |
| 意味監査 | V42 | 設計思想 vs 現行 Trigger の乖離証明 |
| 決定痕跡 | V41 | core = R8 DEFAULT の運用事実 |
| 本契約 | **V43** | 各 World の **意味（勝ち筋）** の正式仕様 |

本ドキュメントは「World とは何か」の **Semantic Contract** 正本である。  
Trigger の書き換え・閾値変更・改善提案は範囲外。

---

## Global Contract

### G1. World の定義

> World は分類ラベルではない。World は **勝ち筋** である。

根拠: V32 ADR「World は AI 最上流の勝ち筋分類である」; V36「World の勝ち筋決定」; V42 設計正本表。

### G2. 対象 World（Canonical）

`core_world` / `midupper_world` / `midhole_world` / `rank7_world` / `mixed_world` / `bug_world`

根拠: `WORLD_LINE_TYPES`（`demo_ticket_optimizer_core.py`）; research `EXISTING_WORLDS` / `DESIGN_SHARE`。

### G3. 設計ミックス（参照）

| World | Design share |
|---|---:|
| core | 30% |
| midupper | 35% |
| rank7 | 15% |
| mixed | 10% |
| bug | 5% |
| midhole | 5% |

根拠: `DESIGN_SHARE` in `world_trigger_saturation.py`（research reference）。

### G4. 本契約と現行 Trigger の関係

現行 `classify_world_line_type` / `TRIGGER_RULES` は **本契約の実装ではない**（V42 Verdict C）。  
本契約は実装を記述せず、**満たすべき意味**を固定する。

---

## 1. `core_world`

### ① World Purpose

能力評価どおりに決着しやすいレース世界。  
「他 World に当てはまらない残り」ではなく、**独立した能力決着の勝ち筋**。

根拠: V42 設計正本; V42 Core Intent; コード周辺の「能力決着」言及（`calc_large_field_topgap_rank7_pressure` が core を能力決着文脈として言及）。

### ② Winning Pattern

上位能力馬が、能力差に沿って勝ち切る。展開ノイズ・混戦・中位穴の寄与が相対的に小さい。

### ③ Required Signals

| Contract Signal | 根拠 |
|---|---|
| `top_gap`（大） | コードに `get_context_top_gap` が存在; V42 が能力決着の必須概念として監査 |
| 能力差（分布の分離: top1 vs 以下） | 設計思想「能力差が結果へ反映」; top_median_gap 等のコード存在 |
| （能力決着を正に示す）非・高 chaos / 非・高 survival 圧 | V42: core は survival DEFAULT であってはならない |

### ④ Optional Signals

| Signal | 根拠 |
|---|---|
| レース格（`race_class` / `grade`、G1 等） | V42 正本例示; metadata に存在 |
| 距離（長距離寄り） | V42 正本例示; `get_context_distance` 存在 |
| 低 `short_field_pressure` | sfp は短距離×多頭 route 圧（能力ではない）— core では低いことが整合 |

### ⑤ Forbidden Signals（誤表現）

| Forbidden as core-positive | 理由（根拠） |
|---|---|
| core = `DEFAULT` / 残余のみ | 設計の独立勝ち筋と矛盾（V41/V42） |
| 高 `chaos` を core 正条件にする | rank7/bug 側の勝ち筋（現行 R5/R6） |
| 高 `short_field_pressure` を core 正条件にする | route 圧; docstring「能力スコアではない」 |
| 高 `late_stop`∧`sustained` を core 正条件にする | midhole Trigger（R4）の領域 |

### ⑥ Expected Characteristics

- 能力差が大きい / TopGap が大きい
- 上位人気・上位能力への結果集中
- 展開・混戦の影響が相対的に小さい
- （任意）格上・長距離で能力が効きやすい

---

## 2. `midupper_world`

### ① World Purpose

上位能力馬が主戦場だが、**能力だけでは決まらず**、展開・適性が勝敗に効く勝ち筋。

根拠: V42 設計正本。

### ② Winning Pattern

能力上位帯の馬が勝つことが多いが、隊列・ペース・適性の差で着順が入れ替わる。  
純粋な能力一本勝ち（core）でも、中位穴広開（midhole）でも、大混戦（rank7）でもない。

### ③ Required Signals

| Contract Signal | 根拠 |
|---|---|
| 上位能力帯の優位（能力分布の上位集中） | 設計「上位能力馬中心」 |
| 展開影響（pace / route / phase 系のいずれか） | 設計「展開も勝敗へ影響」 |
| 適性影響（コース・距離・脚質適合など） | 設計「適性も勝敗へ影響」 |

### ④ Optional Signals

| Signal | 根拠 |
|---|---|
| `difficulty`（中〜） | 現行 Trigger が使用; ただし意味は脚難度（V42: 上位能力そのものではない） |
| `short_field_pressure`（中） | 現行 R2; route 圧として展開の一部近似になり得る |
| 中程度の `top_gap` | core（大）と rank7（小）の中間帯の観測候補 |

### ⑤ Forbidden Signals（誤表現）

| Forbidden | 理由 |
|---|---|
| `difficulty` 高のみで midupper とみなす | 脚難度≠上位能力中心（V42 Wrong Semantic） |
| 高 chaos ∧ 高 pace を midupper 正とする | rank7 領域（R5） |
| 中位 rank 帯の広さを midupper 正とする | midhole 領域 |

### ⑥ Expected Characteristics

- 上位能力・上位人気が中心
- 展開・適性依存が残る
- 波乱度は core より高く、rank7 / midhole より低い

---

## 3. `midhole_world`

### ① World Purpose

中位評価馬まで **十分に勝ち筋が存在する** 世界。

根拠: V42 設計正本。

### ② Winning Pattern

能力・人気の上位だけで閉じず、中位帯の馬が勝ち・好走しうる。  
「穴が一発」ではなく、中位までが妥当な勝ち候補として開いている。

### ③ Required Signals

| Contract Signal | 根拠 |
|---|---|
| 中位評価帯 / 中位 rank・人気帯の競合可能性 | 設計「中位評価馬まで」 |
| 上位独占の弱さ（能力/人気の閉包が弱い） | 勝ち筋の「広さ」 |

### ④ Optional Signals

| Signal | 根拠 |
|---|---|
| `late_stop` / `sustained` | 現行 R4 が使用（ペース生存）。契約上は Optional — 中位帯そのものではない（V42） |
| 中程度の chaos | 展開余地の補助 |

### ⑤ Forbidden Signals（誤表現）

| Forbidden | 理由 |
|---|---|
| late_stop∧sustained のみを midhole の定義とする | 中位評価概念が欠落（V42 Missing） |
| 高 TopGap・強い上位独占を midhole 正とする | core 側特性 |
| 極端な chaos のみ | rank7/bug 側 |

### ⑥ Expected Characteristics

- 中位評価・中位人気に勝ち筋
- 上位一本勝ちが弱い
- 展開による中位浮上の余地

---

## 4. `rank7_world`

### ① World Purpose

展開・混戦・Chaos が **能力評価以上に** 勝敗を決める勝ち筋。

根拠: V42 設計正本; コード `LARGE_FIELD_TOPGAP_*` / compression が rank7 文脈と top_gap 小を結びつける。

### ② Winning Pattern

能力順・人気順から外れやすい。混戦・ペース崩壊・隊列圧などで、下位〜中下位評価も含め結果が動きうる。

### ③ Required Signals

| Contract Signal | 根拠 |
|---|---|
| `chaos`（高） | 設計; 現行 R5; V33 契約内 |
| 展開/混戦圧（`high_pace` / field / compression 等） | 設計; 現行 R5 に high_pace |
| 能力劣後の指標（例: 低 `top_gap`） | 設計「能力以上に」; コードが top_gap 小を rank7 圧に使用（Trigger 本体外） |

### ④ Optional Signals

| Signal | 根拠 |
|---|---|
| 多頭数 | large-field top_gap pressure |
| 短〜中距離 | 同 pressure の補助距離条件 |
| `difficulty`（中〜高） | 混線と併発しうるが bug との境界に注意 |

### ⑤ Forbidden Signals（誤表現）

| Forbidden | 理由 |
|---|---|
| 高 TopGap・強い能力決着を rank7 正とする | core 領域 |
| chaos なしの difficulty のみ | midupper R7 / bug との混同 |

### ⑥ Expected Characteristics

- 波乱・混戦
- Chaos / ペース影響大
- 能力・人気通りになりにくい
- TopGap が小さいことが多い（コード仮説と整合）

---

## 5. `mixed_world`

### ① World Purpose

複数の勝ち筋が **共存**し、単一 World では説明し切れないレース世界。

根拠: V42 設計正本。

### ② Winning Pattern

core / midupper / midhole / rank7 のいずれか一つに還元できず、複数パターンが同時に妥当。券面・評価も単一方針に閉じない。

### ③ Required Signals

| Contract Signal | 根拠 |
|---|---|
| 複数勝ち筋の同時活性（2つ以上の World 意味が競合） | 設計「共存」 |
| （または）単一説明不能の明示 | 設計「一つの World では説明できない」 |

### ④ Optional Signals

| Signal | 根拠 |
|---|---|
| 高 `short_field_pressure` + 複合 OR | 現行 R1（複合圧力の近似） |
| 高 `phase` | 現行 R3 |

### ⑤ Forbidden Signals（誤表現）

| Forbidden | 理由 |
|---|---|
| phase 高のみを mixed の定義とする | 共存概念の欠落（V42） |
| 単一の明確な勝ち筋レースを mixed にする | 他 World の領域 |

### ⑥ Expected Characteristics

- 複数解釈が可能
- 単一 Trigger 勝ち筋に還元しづらい
- （観測上）複合圧力が同時に立ちやすい

---

## 6. `bug_world`

### ① World Purpose

通常の勝ち筋ロジックでは **説明困難な特殊ケース**。

根拠: V42 設計正本。

### ② Winning Pattern

既存の core/midupper/midhole/rank7/mixed の説明枠に乗らない。例外・異常・観測不能に近い振る舞い。

### ③ Required Signals

| Contract Signal | 根拠 |
|---|---|
| 説明不能 / 例外であることの標識（通常ロジック外） | 設計 |
| （または）通常 World 契約を満たさない残差のうち、DEFAULT core ではない特殊残差 | 設計「特殊ケース」; core DEFAULT との区別が必要（V42） |

### ④ Optional Signals

| Signal | 根拠 |
|---|---|
| 極端な `chaos` ∧ 極端な `difficulty` | 現行 R6（弱い近似） |

### ⑤ Forbidden Signals（誤表現）

| Forbidden | 理由 |
|---|---|
| 単なる高 chaos をすべて bug とする | rank7 と衝突 |
| 「どれにも当てはまらない」= bug | それは現行 core DEFAULT であり、設計の core/bug 双方と矛盾 |

### ⑥ Expected Characteristics

- 稀少（Design share 5%）
- 通常説明が破綻
- 安易な DEFAULT と同一視しない

---

## Document index

| Doc | Content |
|---|---|
| `v43-world-semantic-contract.md` | 本ファイル（契約正本） |
| `v43-world-contract-mapping.md` | 現行 Trigger 対応表（⑦） |
| `v43-required-signals.md` | Required / Optional / Forbidden 横断 |
| `v43-contract-completeness.md` | 完成度（⑨） |
| `v43-governance.md` | 統治判定 |

## Guardrails

- Contract restoration only.
- No Trigger / Threshold / Signal / World / Prediction / PE / CE / AI / Production / CSV changes.
- No improvement proposals.
