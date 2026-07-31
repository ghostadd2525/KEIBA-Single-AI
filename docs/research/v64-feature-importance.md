# Version64 — Feature Importance by World

**Date:** 2026-07-28  
**Corpus:** 285R real data only  
**Metric:** oriented effect = winner − loser（odds は低オッズ有利に符号反転） / field_hit = 勝ち馬が当該特徴で場内最良

---

## ① Winner Feature Importance / ③ Top10

### core_world（n=104）

| Rank | Feature | Effect | FieldHit | Hit n/N |
|---:|---|---:|---:|---|
| 1 | popularity_z* | 0.985 | 31.0% | 13/42 |
| 2 | win_prob_z | 0.760 | 21.2% | 22/104 |
| 3 | odds_z | 0.642 | 32.7% | 34/104 |
| 4 | history_z | 0.615 | 19.2% | 20/104 |
| 5 | odds_pct_low | 0.317 | 32.7% | 34/104 |
| 6 | popularity_pct_low* | 0.304 | 31.0% | 13/42 |
| 7 | win_prob_pct | 0.227 | 21.2% | 22/104 |
| 8 | history_pct | 0.201 | 19.2% | 20/104 |

\*popularity は変動ありレースのみ（core 内 42R）。全 core 一般化はしない。

### midupper_world（n=110）

| Rank | Feature | Effect | FieldHit |
|---:|---|---:|---:|
| 1 | win_prob_z | 0.833 | 22.7% |
| 2 | odds_z | 0.717 | 25.5% |
| 3 | history_z | 0.600 | 14.5% |
| 4 | odds_pct_low | 0.321 | 25.5% |
| 5 | win_prob_pct | 0.278 | 22.7% |
| 6 | history_pct | 0.179 | 14.5% |

### midhole_world（n=15）

| Rank | Feature | Effect | FieldHit |
|---:|---|---:|---:|
| 1 | win_prob_z | 1.373 | 33.3% |
| 2 | odds_z | 0.784 | 26.7% |
| 3 | history_z | 0.541 | 33.3% |
| 4 | odds_pct_low | 0.345 | 26.7% |
| 5 | win_prob_pct | 0.240 | 33.3% |
| 6 | history_pct | 0.180 | 33.3% |

### rank7_world（n=65, V44）

| Rank | Feature | Effect | FieldHit |
|---:|---|---:|---:|
| 1 | history_z | 0.707 | 20.0% |
| 2 | win_prob_z | 0.690 | 15.4% |
| 3 | odds_z | 0.681 | 30.8% |
| 4 | odds_pct_low | 0.338 | 30.8% |
| 5 | win_prob_pct | 0.273 | 15.4% |
| 6 | history_pct | 0.215 | 20.0% |

### mixed_world（n=56）

| Rank | Feature | Effect | FieldHit |
|---:|---|---:|---:|
| 1 | history_z | 0.679 | 17.9% |
| 2 | odds_z | 0.644 | 17.9% |
| 3 | win_prob_z | 0.551 | 12.5% |
| 4 | odds_pct_low | 0.281 | 17.9% |
| 5 | win_prob_pct | 0.234 | 12.5% |
| 6 | history_pct | 0.220 | 17.9% |

### bug_world

サンプル 0 — Top10 なし。

---

## ② Losing Feature（負け馬側）

全 World で共通（符号は同方向）:

| Losing 傾向 | 意味（測定） |
|---|---|
| 低 `win_prob_z` / 低 `win_prob_pct` | 場内相対確率が低い |
| 高 `odds`（低 `odds_pct_low`） | 長めオッズ側に偏る |
| 低 `history_z` / 低 `history_pct` | history_score が場内で弱い |

World 差は **Losing の種類ではなく、Winner 側の順位入れ替え**（core/midupper=win_prob 首位、rank7/mixed=history 首位）。

### 脚質（勝ち − 負け share）

| World | 正リフト Top | 負リフト |
|---|---|---|
| core | 逃げ +0.14, 先行 +0.06 | 差し -0.09 |
| midupper | 先行 +0.08, 逃げ +0.06 | 差し -0.08 |
| midhole | **差し +0.08** | （逃げは弱） |
| rank7 | 逃げ +0.10, 先行 +0.08 | 差し -0.08 |
| mixed | 逃げ +0.12 | 差し -0.09 |

---

## ④ Stable Feature（World 内・top_gap 中央値分割）

両側で同符号かつ |effect|≥0.05:

| World | Stable |
|---|---|
| core / midupper / midhole / rank7 / mixed | `win_prob_z`, `history_z`, `odds_z`, `win_prob_pct`, `history_pct`, `odds_pct_low` |

→ 馬特徴の勝ち側方向は **World 内でも安定**（分割しても逆転しない）。

---

## ⑤ Context Feature

- top_gap 分割による **馬特徴の符号逆転は検出されず**（context_features リスト空）。  
- 代わりに **レース文脈そのもの**が World を分ける（Strategy Selector）:

| World | top_gap | top_monopoly | ability_subordinate | field_size | distance |
|---|---:|---:|---:|---:|---:|
| core | 0.035 | 0.149 | 0.824 | 12.8 | 1749 |
| midupper | 0.028 | 0.118 | 0.861 | 15.3 | 1850 |
| midhole | 0.038 | 0.127 | 0.810 | 15.1 | 1853 |
| rank7 | **0.012** | **0.104** | **0.938** | **16.1** | 1624 |
| mixed | 0.025 | 0.110 | 0.875 | 16.3 | **1271** |

Context 依存の **勝ち方**（相関）は `v64-cross-world-analysis.md` を参照。

---

## データ制約

- popularity: 285R 中 **240R が欠損/一定** → 原則除外（core 42R のみ参考）  
- chaos / high_pace / aptitude 等: **285R runner JSON に列なし** → 未使用（推測で補完しない）
