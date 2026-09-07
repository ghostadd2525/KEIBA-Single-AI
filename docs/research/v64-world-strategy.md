# Version64 — World Strategy Discovery

**Date:** 2026-07-28  
**Subject:** World ごとの勝利メカニズム（Strategy Selector 視点）  
**Locks:** PE / Prediction / Trigger / Signal / World / Threshold / Production — **変更・実装禁止**  
**Corpus:** real_285R のみ（`real_285r_corpus.json` + dual-eval World ラベル + fixture 距離/馬場）  
**Parents:** V35 / V62 / V63（PE 直接結合では安全 ROI 未証明）

---

## 結論（1行）

馬特徴の極性は World 間でほぼ共通だが、**重要度順位・脚質リフト・レース文脈（top_gap 等）・文脈相関の符号**で差がある。**異なる Strategy の萌芽は確認**（Governance **B**）。bug は n=0 で未証明。

---

## 方法（推測禁止）

| 項目 | 定義 |
|---|---|
| ラベル | **hybrid**: core/midupper/midhole/mixed = Legacy；rank7/bug = V44（Legacy に 0 件のため） |
| 馬特徴 | レース内 z / percentile：`win_prob`, `history_score`, `odds`（popularity は変動ありの 45R のみ） |
| レース概念 | win_prob 分布から算出（W-S1 同型）：`top_gap`, `ability_separation`, `upper_ability_band`, `mid_eval_band_open`, `top_monopoly`, `ability_subordinate` |
| Importance | winner_mean − loser_mean（向き付け後）＋ field_hit_rate |
| 非対象 | World Weight、PE 加点、chaos 等の非 285R 列（コーパスに無いものは使わない） |

**サンプル:**

| World | n | ラベル源 |
|---|---:|---|
| core | 104 | Legacy |
| midupper | 110 | Legacy |
| midhole | 15 | Legacy（小標本） |
| rank7 | 65 | V44 |
| mixed | 56 | Legacy |
| bug | **0** | 不足 |

---

## ⑥ Strategy Candidate（World = Strategy Selector）

> PE に Weight する話ではない。各 World で「何を読むべきか」の整理。

### core_world（n=104）

→ **能力寄り（win_prob）＋短めオッズ＋history**。脚質は **逃げ / 先行** が勝ち馬で過剰。  
レース文脈は **top_gap・top_monopoly が高め**（平均 top_gap=0.035, monopoly=0.149）、頭数やや小。  
popularity が取れる部分集合（42R）では popularity_z 効果大だが **全 core への一般化は不可**。

### midupper_world（n=110）

→ **win_prob 最優先**、次いで odds / history。脚質は **先行 > 逃げ**。  
文脈は core より top_gap・monopoly が低い（0.028 / 0.118）、頭数大。

### midhole_world（n=15・注意）

→ win_prob 効果は最大（effect=1.37）だが **n 小で不安定**。脚質は唯一 **差しリフト正**。  
文脈 top_gap は高め（0.038）。確定戦略というより **仮説候補**。

### rank7_world（n=65, V44）

→ Top1 特徴が **history_z**（core/midupper は win_prob_z）。  
文脈は **top_gap 最低（0.012）・ability_subordinate 最高（0.938）・頭数大**。  
`corr(field_size, winner_win_prob_pct) = -0.11`（core は +0.16）→ 多頭数で本命度が勝ちに結びつきにくい。

### mixed_world（n=56）

→ **history_z が首位**、win_prob は相対的に弱い（effect 0.55）。脚質は逃げ。  
距離平均が短い（1271m）。`corr(top_gap, winner_history_pct) = -0.19`（他 World は概ね非負）→ gap が大きいほど history 勝ちが弱い。

### bug_world（n=0）

→ **抽出不可**。285R Legacy/V44 ともに 0 件。

---

## World は加点ではなく Selector

| 層 | 役割（本フェーズの解釈） |
|---|---|
| Race context（top_gap 等） | **どの Strategy を選ぶか** |
| Horse feature ranking | **選んだ Strategy 内で何を読むか** |
| PE Weight | **本フェーズ対象外**（V63 で安全 ROI 未証明） |

---

## 証明ステートメント

**「Worldごとに異なる Strategy が存在するか」**

- **部分的に Yes（B）:** 重要度順位（win_prob vs history）、脚質（差しは midhole のみ正）、レース文脈、文脈相関の符号逆転が測定された。  
- **完全分離は No:** 馬特徴の勝ち側極性は全 World で同方向（win_prob↑ / odds↓ / history↑）。  
- **bug は未証明。**

数値正本: `docs/research/_v64-sim.json`
