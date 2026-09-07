# Version36 — Boundary Analysis（Original Flow + WIC Consumers）

**Status:** Architecture only — **not implemented**  
**Date:** 2026-07-28  
**Parent:** `v36-world-pe-integration.md`

---

## ③ Original Design Restoration

### 設計思想から復元すべきデータフロー

V32/V33 および本フェーズ調査対象を統合した **本来フロー**:

```text
Race Context
  → [WIC / Signal Service]          # 条件信号の正本（V32 P4 / V33）
  → World                           # 勝ち筋分類（最上流の決定）
  → SubWorld                        # 勝ち筋の細分
  → Required / Role                 # 勝ち筋に必要な役割・必須枠
  → Candidate Pool                  # 勝ち筋に属する評価・購入母集団
  → PE（score / rank / pick policy）# 母集団＋勝ち筋政策で順位を決定
  → CE（投影・信頼度・説明）         # PE 結果の構造化（決定の後段）
  → Prediction                      # 公開。World を落とさない
```

**CE の位置:** 本来 CE は「PE の結果を投影する層」であり、World の **決定層ではない**。  
現行 CorePipeline が World を CE 末尾で付けているのは、決定と投影の混線である。

### 現行実装フロー（V35 証明）

```text
Race Context
  → Features
  → Scorer / Ranker          # PE 相当・World なし
  → Prediction               # world 欠落 / mapper None
  → WorldClassifier          # 事後ラベル
  → CE WorldMeta 添付
  →（別系統）Candidate Pool → SubWorld guards → Purchase
```

### 差分表

| 観点 | 本来 | 現行 | 差分種別 |
|------|------|------|----------|
| World の順序 | PE / Prediction **前** | Prediction **後** | Order inversion |
| World の役割 | 勝ち筋 **決定** | ラベル / メタ | Responsibility inversion |
| Pool と PE | Pool → PE | PE → Pool | Pipeline mismatch |
| Required | World 直後の契約消費者 | Core ranking 非入力 | Missing consumer |
| CE | PE 結果の投影 | World 添付の受け皿 | Annotator misuse |
| Prediction 契約 | world 保持 | drop / null | Contract drop |
| WIC | World の入力正本 | default 希釈 + Research のみ再構成 | Signal dilution |

### 復元の意味（実装しないが設計として固定）

「復元」とは 116列 CSV への回帰ではなく（V32）、次を同時に満たすこと:

1. WIC 充足信号で World を **早期**に分類する  
2. World 決定が Required / Pool に渡る（選択脊柱）  
3. **同じ World 決定が PE の入力契約になる**（評価脊柱）  
4. Prediction が World を破棄しない（公開契約）

1+2 だけでは Hit は動かない（V35）。3 が本フェーズの核心。

---

## ④ Contract Boundary — WIC → Consumers

### 契約階層

```text
World Input Contract (V33)
        │
        ▼
 World decision record
   { world, sub_world, policy_id?, required_roles?, pool_constraints? }
        │
        ├─► Required / Role          【正式 Consumer】
        ├─► Candidate Pool           【正式 Consumer】
        ├─► PE（score/rank policy）  【正式 Consumer — V36 で欠落を認定】
        ├─► CE（投影・説明）         【派生 Consumer — 決定しない】
        ├─► Prediction facade        【伝播 Consumer — 破棄禁止】
        ├─► Optimizer / Delete       【下流 Consumer — Pool/PE 経由】
        └─► Challenge / Purchase     【下流 Consumer — Pool 経由】
```

### Consumer 正式整理

| Consumer | WIC 直接? | World decision 直接? | 契約上の義務 | 現状 (V35) |
|----------|:---------:|:--------------------:|--------------|------------|
| WorldClassifier | **Yes** | Producer | L1/L2 充足で分類 | Partial / default 寄り |
| SubWorld | No | **Yes** | World に整合した細分 | 生成はするが PE 非連動 |
| Required / Role | No | **Yes** | 勝ち筋の必須枠を宣言 | Core に未結合 |
| Candidate Pool | No | **Yes** | 勝ち筋母集団を構成 | post-score・購入側 |
| **PE** | No* | **Yes（必須）** | World policy を順位に反映 | **未契約・未接続** |
| CE | No | Annotate only | PE 結果 + World 参照の投影 | Annotate only |
| Prediction | No | Pass-through | world を落とさない | Drop / null |
| Optimizer / Delete | No | Indirect | Pool/PE 出力に従う | SubWorld ガード程度 |
| Signal Service | Producer | — | WIC 供給（未実装） | NO-GO pending ROI |

\* PE は WIC 生信号を直接読まないのが望ましい（責務分離）。読むのは **World decision / policy**。WIC は World の入力に閉じる（V32 P4）。

### 境界ルール（設計）

1. **WIC の第一 Consumer は World のみ**（Feature/PE が WIC を横取りしない）  
2. **PE の World 入力は decision/policy**であり、生 difficulty の再解釈ではない  
3. **CE は World を決定に使わない**（投影・説明に限る）  
4. **Prediction は World フィールドを契約必須**とする（計算結果の一部として）  
5. **Pool は PE を代替しない** — Pool は集合、PE は順位

### 契約切断（V35）と本境界の対応

| V35 ID | 境界上の位置づけ |
|--------|------------------|
| MC-1 WIC→Scorer | 原則 **禁止に近い**（PE は WIC 生ではなく World policy） |
| MC-2 World→Ranker | **必須辺**（本フェーズ推奨 I3） |
| MC-3 World→Required→Pool→PE | 選択脊柱 + 評価脊柱の **両方**が必要 |
| MC-4/5 Prediction drop | 伝播 Consumer 義務違反 |
| MC-8 Signal Service | WIC Producer（別ゲート） |
