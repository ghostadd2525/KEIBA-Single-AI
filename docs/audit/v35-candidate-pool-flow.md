# Version35 — Candidate Pool → PE Data Flow

**Phase:** V35 PE Dependency Audit  
**Mode:** Research / Audit only  
**Date:** 2026-07-28

---

## ③ Candidate Pool Dependency

### 設計意図（モジュール境界）

`CandidateEvaluationProjector` / `CorePipeline` モジュール docstring:

> No Candidate Pool or Repick function is imported or called.  
> Every runner in the probability input for the requested race is projected to CE.

→ **Candidate Pool は CE/PE ranking の上流ではない。** むしろ **下流（Win5 選択）**。

### データフロー（実装）

```
[全出走] FeatureLoader
    ↓
Scorer / Ranker → model_rank, win_prob   ← Prediction Hit の本体
    ↓
World / SubWorld ラベル（事後）
    ↓
CE candidates（全馬投影）
    ↓ ─── ここまでが Single Prediction 経路 ───
[Win5] build_candidate_pool(race_df, meta)
    ↓  sort by win_prob（既に確定した確率）
    ↓  filter / attach pool fields
SubWorld / route / hard guard / re_pick
    ↓
Purchase / ticket selection
```

### Candidate Pool が変化した場合の PE への影響

| 変化対象 | Prediction ranking / Hit top pick | Win5 Purchase / 券面 |
|----------|-----------------------------------|----------------------|
| Pool サイズ・フィルタ変更 | **影響なし**（Pool は ranking 後） | 影響あり得る |
| Pool 内優先度（`pool_priority` 等） | **影響なし** | 影響あり得る |
| SubWorld hard guard で除外 | **model_rank 不変** | 購入候補が変わる |
| Required / Role による必須枠 | Core ranking **非入力** | 選択ロジック側 |

### `build_candidate_pool` の入口（要約）

出典: `demo_ticket_optimizer_core.py` L9412〜

1. （任意）CE-V2 temperature — Flag OFF 時 identity  
2. rank10–15 snapshot を meta に添付  
3. `race_df.sort_values("win_prob", ascending=False)`  
4. 行ごとに pool 候補 dict を構築  

**入力の主キーは既計算の `win_prob` / `model_rank`。** World ラベルが pool のソートキーではない。

### PE（Prediction）視点の結論

Candidate Pool 変化 → **PE top pick / Hit 層は設計上不変。**  
Candidate Pool 変化 → **Purchase / Challenge 券面は可変（別系統）。**

V34 で Hit/Purchase/rank710 がすべて不动だった理由の一端は、Shadow AB が **PE pick 凍結**に加え、World 再分類が **Pool→Purchase の本番経路に接続されていなかった**（Research Shadow）ためでもある。詳細は `v35-frozen-point.md`。
