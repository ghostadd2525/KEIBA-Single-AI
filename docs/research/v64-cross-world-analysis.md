# Version64 — Cross World Analysis

**Date:** 2026-07-28  
**Question:** 同じ特徴が World によって逆効果か？  
**Corpus:** 285R only

---

## ⑦ Cross World — 馬特徴の極性

| 結果 | 内容 |
|---|---|
| 符号逆転（winner−loser effect） | **0 件** |
| 共通の勝ち側 | `win_prob↑`, `history↑`, `odds↓`（全 usable World） |

→ 「top_gap を馬特徴として core+ / rank7−」のような **馬内相対効果の逆符号は、本データでは未検出**。  
（top_gap はレース定数のため、勝ち馬 vs 負け馬の差分特徴にはならない。）

---

## Cross World — 重要度順位の差（Strategy 差）

| Feature | core | midupper | midhole | rank7 | mixed |
|---|---:|---:|---:|---:|---:|
| win_prob_z rank | 2* | **1** | **1** | 2 | 3 |
| history_z rank | 4 | 3 | 3 | **1** | **1** |
| odds_z rank | 3 | 2 | 2 | 3 | 2 |

\*core の rank1 は popularity（部分標本）。popularity 除外時は win_prob が首位級。

**解釈（測定）:** 同じ特徴でも **読む優先順位が World で違う**（完全逆効果ではないが Strategy 差）。

---

## Cross World — レース文脈プロファイル

| 指標 | 高い World | 低い World | span |
|---|---|---|---:|
| top_gap | midhole 0.038 / core 0.035 | **rank7 0.012** | 0.026 |
| top_monopoly | core 0.149 | rank7 0.104 | 0.045 |
| ability_subordinate | **rank7 0.938** | midhole 0.810 | 0.128 |
| field_size | mixed/rank7 ~16 | core 12.8 | 3.5 |
| distance | midupper/midhole ~1850 | **mixed 1271** | ~580 |

→ World はまず **レース状態の Selector** として分離している。

---

## Cross World — 文脈×勝ち馬強度の相関（符号逆転）

閾値: |r|≥0.08 かつ正負 World が共存。

| Metric | + Worlds | − Worlds | span |
|---|---|---|---:|
| corr(top_gap, winner_win_prob_pct) | midhole (+0.21) | mixed (−0.09) | 0.30 |
| corr(top_gap, winner_history_pct) | midhole (+0.10) | **mixed (−0.19)** | 0.29 |
| corr(ability_subordinate, winner_history_pct) | **mixed (+0.19)** | midhole (−0.10) | 0.29 |
| corr(field_size, winner_win_prob_pct) | **core (+0.16), midupper (+0.09)** | **rank7 (−0.11)** | 0.28 |

### 例（ユーザー例に近い測定）

| 主張に近い測定 | Evidence |
|---|---|
| top_gap と「本命勝ち」の関係が World で逆 | midhole で正相関、mixed で負相関 |
| 頭数と本命勝ちが core+ / rank7− | core r=+0.16、rank7 r=−0.11 |

※これは **PE 加点の推奨ではない**。Strategy Selector として「同じ文脈量が勝ち方と逆向きに結びつく」証拠。

---

## Cross World — 脚質

| Style | + Worlds | − Worlds |
|---|---|---|
| **差し** | midhole (+0.08) | core / midupper / rank7 / mixed（いずれも −0.08 前後） |

差しは **midhole でのみ勝ち馬過剰** — 明確な逆効果候補。

---

## Jaccard（Top5 特徴集合）

mean pairwise Jaccard ≈ **0.87**（馬特徴セットは高重複）。  
→ 単独では C 寄りだが、文脈・相関・脚質を含めると **B（一部重複・一部差）**。

---

## まとめ

1. 馬特徴の勝ち極性は共通（逆符号なし）。  
2. 順位・文脈・相関・脚質で World 差あり。  
3. bug は比較不能（n=0）。
