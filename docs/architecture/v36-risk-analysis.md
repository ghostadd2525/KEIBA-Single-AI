# Version36 — Migration Difficulty & Risk Analysis

**Status:** Architecture only — **not implemented**  
**Date:** 2026-07-28  
**Parent:** `v36-world-pe-integration.md`

---

## ⑤ Migration Difficulty

| ID | 案 | 難易度 | 理由 |
|----|-----|:------:|------|
| I1 | World → Candidate Pool | **Medium** | Pool/meta 経路は既存。ただし post-score 前提の書き換えと Purchase 回帰が必要 |
| I2 | World → Required / Role | **Medium** | Required 契約の定義・充足判定の新設/強化。PE 非接続なら効果限定 |
| I3 | World → PE | **High** | Scorer/Ranker の入力契約変更。Hit 分布・校正・AB 設計が必須。CorePipeline 順序の逆転 |
| I4 | World → CE only | **Low** | 現行に近く変更小。ただし設計復元にならない |
| I5 | Facade pass-through | **Low** | キー復元のみ。計算非連動 |
| I6 | World → Features | **High** | 特徴・モデル・日次供給・V31 列契約まで波及 |

**推奨案 I3 の難易度は High** — これが正しい接続であることの否定ではない。正しいが重い。

---

## ⑥ Risk Analysis — 影響範囲マトリクス

凡例: **H** 高影響 / **M** 中 / **L** 低 / **—** 実質なし / **!** 見かけ上のみ

### I1 World → Candidate Pool

| 対象 | 影響 | 内容 |
|------|:----:|------|
| Prediction | L / — | 全馬 PE のままなら top pick 不変（V35 再発） |
| PE | — | 入力不変 |
| CE | L | Pool と CE 全馬投影の不一致が目立つ |
| Role | M | Pool 制約と Role の整合が必要 |
| Candidate Pool | **H** | 主変更点 |
| Optimizer | **H** | 母集団変化 |
| Delete | **H** | 削除対象・ガード再定義 |

### I2 World → Required / Role

| 対象 | 影響 | 内容 |
|------|:----:|------|
| Prediction | L / — | Required が PE に戻らなければ不変 |
| PE | L | 間接のみ |
| CE | L | |
| Role | **H** | 主変更点 |
| Candidate Pool | **M** | Required 起因の下限・強制入池 |
| Optimizer | **M** | 制約付き最適化 |
| Delete | **M** | Required 保護で削除抑制 |

### I3 World → PE（推奨）

| 対象 | 影響 | 内容 |
|------|:----:|------|
| Prediction | **H** | top pick / 順位分布が World 連動 |
| PE | **H** | 主変更点（入力契約・政策） |
| CE | **M** | 投影元が変わる。WorldMeta は決定後の真実と一致しうる |
| Role | M | PE policy と Role の二重規定を避ける必要 |
| Candidate Pool | M | PE 前に Pool するなら集合制約とセット；現行順維持なら後段のまま |
| Optimizer | M〜H | 順位・候補変化の下流 |
| Delete | M | 新順位に対する削除政策の再検証 |

**特有リスク（I3）:**

- World 誤分類 → 系統的な Hit 劣化  
- Feature 信号と World policy の二重計上  
- V34 型 Shadow で PE を凍らせると再び因果が消える（実験設計リスク）  
- midupper 飽和（V22/V27）のまま PE 接続すると、勝ち筋多様化せず一方向バイアスが増幅

### I4 World → CE only

| 対象 | 影響 | 内容 |
|------|:----:|------|
| Prediction | — / ! | 計算不変。表示だけ変わる場合あり |
| PE | — | |
| CE | **M** | meta / confidence 説明 |
| Role / Pool / Optimizer / Delete | —〜L | 既存購入経路以外はほぼ不変 |

**リスク:** 「接続したように見える」偽修復。

### I5 Facade only

| 対象 | 影響 | 内容 |
|------|:----:|------|
| Prediction | ! | フィールド復活のみ |
| 他 | — | |

### I6 World → Features

| 対象 | 影響 | 内容 |
|------|:----:|------|
| Prediction | **H** | 間接的に全順位変動 |
| PE | **H** | 入力分布変化 |
| CE | M | |
| Role / Pool | L〜M | |
| Optimizer / Delete | M | |
| （追加）Feature / CSV / Signal | **H** | V31 契約再燃 |

---

## リスク要約（設計判断用）

| 案 | Prediction を動かすか | 責務の自然さ | 主な危険 |
|----|:---------------------:|:------------:|----------|
| I1 | 現行 PE では No | 選択には自然 | Hit 不変の温存 |
| I2 | 単体では No | 契約には自然 | 紙の Required |
| **I3** | **Yes** | **決定に最も自然** | 誤分類の直撃・移行 High |
| I4 | No | 説明のみ | 偽接続 |
| I5 | No | 低い | 偽接続 |
| I6 | Yes | 低い（漏洩） | 契約・再学習爆発 |

詳細推奨: `v36-recommendation.md`。
