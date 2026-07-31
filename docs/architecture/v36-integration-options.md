# Version36 — Integration Options & Influence Analysis

**Status:** Architecture only — **not implemented**  
**Date:** 2026-07-28  
**Parent:** `v36-world-pe-integration.md`

---

## ① World Integration Point — 候補一覧

「World をどの層へ渡すのが最も自然か」を、**消費点（Consumer edge）**として列挙する。  
World **生成**自体は WIC → WorldClassifier で早期に行う前提（V32/V33）。ここでの問いは **誰が World を読んで振る舞いを変えるか**。

| ID | 接続 | 一言 |
|----|------|------|
| **I1** | World → Candidate Pool | 勝ち筋で候補集合を絞る |
| **I2** | World → Required（+ Role） | 勝ち筋で必須枠・役割を固定する |
| **I3** | World → PE（Scorer / Ranker / top-pick policy） | 勝ち筋で評価・順位政策を変える |
| **I4** | World → CE（Projector / Confidence / explain） | 評価行・信頼度・説明に載せる |
| **I5** | World → Prediction facade only | 公開 JSON に world を戻す（計算は不変） |
| **I6** | World → Features（world-conditioned feature set） | 特徴段階で勝ち筋を埋め込む（PE の手前の別経路） |

調査対象チェーンとの対応:

```text
Race Context → World → SubWorld → Required → Candidate Pool → PE → Prediction
                 │         │          │            │         │
               generate   refine     I2           I1        I3
                                                         Prediction←I5
                                                         CE←I4
```

---

## ② Influence Analysis

### I1 — World → Candidate Pool

| 項目 | 内容 |
|------|------|
| **責務** | 勝ち筋に合う馬だけを購入・選択の母集団にする |
| **影響範囲** | Win5 Pool / Purchase / Delete / Optimizer 入口。Core 全馬 Rank は不変のままになりやすい |
| **副作用** | Single Prediction（全馬 top）と Pool が乖離し続けるリスク。V35 と同型の「World 変わっても Hit 不変」が残り得る |
| **自然さ** | Win5 券面設計には自然。Prediction Engine の勝ち筋決定としては **不足** |

### I2 — World → Required（+ Role）

| 項目 | 内容 |
|------|------|
| **責務** | 勝ち筋ごとの必須役割・必須候補を契約化する |
| **影響範囲** | Required 充足チェック、Role 割当、Pool 下限・再ピック制約 |
| **副作用** | Required が PE に戻らない限り top pick は不変。過剰 Required は券面爆発 / 購入不能 |
| **自然さ** | World→SubWorld の直後として自然。単体では Prediction を動かさない |

### I3 — World → PE

| 項目 | 内容 |
|------|------|
| **責務** | 勝ち筋に応じたスコア重み・順位政策・（任意）評価対象集合を PE が消費する |
| **影響範囲** | Scorer / Ranker / PE top pick / ひいては Prediction Hit 層 |
| **副作用** | World 誤分類が直接 Hit を汚染。World と Feature の二重カウント。CE との責務境界が再定義必要 |
| **自然さ** | 「World が勝ち筋を決定し Prediction がそれに従う」に **最も直結** |

### I4 — World → CE

| 項目 | 内容 |
|------|------|
| **責務** | 確定 Rank に WorldMeta を付け、Confidence/Explain を調整する |
| **影響範囲** | CE rows / explain / 観測。Rank 本体は現状どおり不動になりやすい |
| **副作用** | **現行に近い失敗モード**（ラベルはあるが Prediction 非連動）の温存 |
| **自然さ** | 説明可能性には自然。勝ち筋 **決定** 層としては不適切 |

### I5 — World → Prediction facade only

| 項目 | 内容 |
|------|------|
| **責務** | API/UI に world を再掲する |
| **影響範囲** | 契約表示のみ |
| **副作用** | 見かけの整合と計算の乖離（監査上の偽接続） |
| **自然さ** | 表示修復のみ。設計復元ではない |

### I6 — World → Features（条件付き特徴）

| 項目 | 内容 |
|------|------|
| **責務** | WIC/World 政策を特徴量に焼いて Scorer に間接入力 |
| **影響範囲** | FeatureGenerator / モデル入力次元 / 全 Downstream |
| **副作用** | World と Feature の責務混線。再学習・安定性コスト大。V32 の「列数ではなく Signal 契約」と衝突しやすい |
| **自然さ** | 物理的には PE 前だが、**World 層の責務を Feature に漏洩**させる |

---

## 候補の相対位置（責務 ent）

```text
勝ち筋の「決定」に近い ←────────────────→ 「表示」に近い

  I3 PE          I2 Required    I1 Pool     I6 Features*    I4 CE     I5 Facade
  (policy)       (must-bind)    (set)       (leak)          (meta)    (display)

* I6 は効果は強いが責務境界が悪い
```

---

## 複合は認めつつ主接続は1点

設計上、**生成順**は常に:

```text
WIC → World → SubWorld → (I2 Required) → (I1 Pool) → (I3 PE) → Prediction
```

本フェーズの「1つの推奨接続点」は、この鎖の中で **Prediction を勝ち筋に従わせるために欠かせない辺** を指す。  
それが欠けると I1/I2 だけでも V35 再発する。詳細は `v36-recommendation.md`。
