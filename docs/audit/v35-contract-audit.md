# Version35 — World Input Contract（WIC）Consumer Audit

**Phase:** V35 PE Dependency Audit  
**Mode:** Research / Audit only  
**関連:** V32 ADR / V33 WIC Definition / V34 Shadow AB  
**Date:** 2026-07-28

---

## ⑥ Contract Audit

### WIC が想定する Consumer（設計・V33）

V33 の World Input Contract は、difficulty / chaos 等の信号層（L0/L1/L2）を **World 分類の入力**として定義し、DEFAULT 0.5 / chaos 0 を World **政策**として禁止する方向。

想定フロー（設計）:

```
Race signals (WIC)
  → World / SubWorld classification
  →（将来）選択・評価・説明に伝播
```

### 実装上の Consumer 一覧

| Consumer | WIC / World 信号を受け取るか | 受け取り方 | Prediction 反映 |
|----------|------------------------------|------------|-----------------|
| `WorldClassifier` / `classify_world_line_type` | **Partial** | `detect_race_meta` 由来 meta（Production は default 寄り difficulty） | ラベルのみ |
| V34 `reconstruct_wic_difficulty` | **Yes（Research）** | FeatureLoader frame から再構成 | World ラベルのみ（PE frozen） |
| Scorer | **No** | — | — |
| Ranker | **No** | — | — |
| Candidate Pool | **Indirect** | meta キー・後段 SubWorld | Purchase 側 |
| Required / Role | **No / weak** | Core 契約外 | — |
| CE Projector | **Annotate only** | `WorldMeta` 文字列 | Rank 不変 |
| `predict_full_bundle` | **Pass-through** | `world` / `sub_world` キー | バンドル閲覧用 |
| `predict_ranking` | **Drop** | キーなし | 公開順位から切断 |
| Single prediction mapper | **Drop** | `world: None` | 評価オブジェクトから切断 |
| Signal Service | **未実装** | V34 で Signal Service design **NO-GO**（ROI 未証明） | — |

### 契約伝播図

```
[WIC signals]
    │
    ├─► (Production meta) ──► WorldClassifier ──► world/sub_world label
    │                              │
    │                              ├─► CE WorldMeta          (annotate)
    │                              ├─► predict_full_bundle   (pass)
    │                              ├─► predict_ranking       ✂ DROP
    │                              └─► mapper evaluation     ✂ NULL
    │
    ├─► Scorer / Ranker / PE top pick              ✂ NO EDGE
    │
    └─► (V34 Shadow only) reconstruct → reclassify
            └─► frozen PE pick                     ✂ NO HIT EDGE
```

---

## ⑦ Missing Connection（契約切断一覧）

改善は行わない。切断の列挙のみ。

| ID | 設計上期待されうる接続 | 実装状態 | 切断種別 |
|----|------------------------|----------|----------|
| MC-1 | WIC difficulty → Scorer 再重み / 特徴 | 接続なし | **Input gap** |
| MC-2 | World label → Ranker / top pick | Rank が World 前に確定 | **Order inversion** |
| MC-3 | World → Required → Pool → PE | Pool は PE 下流；Required は Core 非入力 | **Pipeline mismatch** |
| MC-4 | CE world → `predict_ranking` | キー省略 | **Facade drop** |
| MC-5 | Prediction evaluation.world | `None` 固定 | **Mapper null** |
| MC-6 | WIC → Production FeatureLoader 日常値 | default 0.5 寄り（V30/V31） | **Signal dilution** |
| MC-7 | Shadow World → live Purchase | AB は frozen pick / Research | **Experiment isolation** |
| MC-8 | Signal Service as WIC owner | 未実装（V34 NO-GO） | **Missing component** |

### 設計図 vs 実装図

**設計（調査対象として提示されたチェーン）:**

```
Race Context → World → SubWorld → Required → Candidate Pool → PE → CE → Prediction
```

**実装（証明されたチェーン）:**

```
Race Context → Features → PE/CE Score+Rank → (meta) → World/SubWorld label
                         ↘ Prediction (world dropped)
                         ↘ Win5 Pool → SubWorld guards → Purchase
```

---

## 最終判定

### **C — World does not effectively propagate to PE**

根拠:

1. Scorer/Ranker（PE ranking 本体）は World を参照しない。  
2. World は rank **後**のラベル生成。  
3. 公開 Prediction は facade/mapper で World を落とす。  
4. Candidate Pool は PE の上流ではなく下流。  
5. V34 はそれに加え PE pick を凍結し、World→Hit の因果を観測不能にした（実験設計と実装が同方向）。

**A**（正しく消費）でも **B**（部分消費で ranking に効く）でもない。  
Win5 Purchase への SubWorld **Medium** 影響は「PE が World を消費」には数えず、**Prediction Engine 経路の実効伝播なし**と判定する。

---

## 成果物インデックス

| ファイル | 内容 |
|----------|------|
| `v35-pe-responsibility.md` | ① PE 責務 |
| `v35-pe-dependency.md` | ② 参照一覧 |
| `v35-candidate-pool-flow.md` | ③ Pool フロー |
| `v35-frozen-point.md` | ④ V34 凍結点 |
| `v35-world-influence-matrix.md` | ⑤ 影響度行列 |
| `v35-contract-audit.md` | ⑥⑦ 契約・切断 + 最終判定 |
