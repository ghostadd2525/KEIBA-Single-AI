# Version83 — Interaction Integration Design

**Date:** 2026-07-28  
**Status:** Design ONLY — **実装禁止**  
**Parents:** V82 Interaction Contract / Priority / V81 Discovery / V80 Attribution（単体 Weight Strategy Hit−133）  
**Locks（本フェーズ・変更禁止）:** Production / Trigger / Blueprint / World / **Interaction Contract**  
**非目的:** PE コード変更・本番 Cutover・Hit 改善実装

---

## 問題

V82 は World ごとの Interaction Must / Aux / Forbidden と Priority を定義した。  
未定義なのは:

> Interaction が **成立したとき、PE のどの出力層に、どう作用するか**

本設計は作用方式（Integration Mode）の比較と推奨候補選定まで。Contract 本文は変更しない。

---

## 前提アーキテクチャ（概念・非実装）

```text
[変更禁止層]
  Trigger → World Label（CEW 観測可 / Production Trigger 非変更）
  Blueprint / World Meaning
  Interaction Contract（V82 固定）

[本設計の対象 = Integration Adapter（将来 Shadow 用の概念層）]
  Mode ∈ {Bonus, Gate, Selector, RankSwap, Confidence}
  Input:  BaseScore / BaseRank / BaseConfidence（Legacy PE 出力）
        + InteractionFireVector（Contract Priority に従う発火・非発火）
  Output: AdaptedScore / AdaptedRank / AdaptedConfidence
        ※ Production PE には接続しない（本フェーズ）
```

| 層 | 権限 |
|---|---|
| Contract | 読取専用（V82） |
| Integration Mode | 本設計で定義。実装・本番接続は別 Decision |
| Legacy PE | Fallback 正本（V78/V80 同様） |

---

## 五方式の定義

### ① Bonus

```text
score' = BaseScore + Σ_k w_k · φ_k(Interaction_k)
```

- Interaction を **加点項**として Base に加算。  
- 順位は score' の再ソートで間接変化し得る。  
- V80 単体 Weight に最も近い構造（線形加算族）。

### ② Gate

```text
IF Must Interactions が成立:
    evaluate with Interaction-aware path
ELSE:
    discard / defer / Legacy only（設計選択肢）
```

- Interaction **成立時のみ**当該 World の評価パスを許可。  
- 不成立時は評価抑制または Legacy 固定。  
- 「読むな」を強制する方式。

### ③ Selector

```text
path = argmax_priority { fired Must/Aux Interactions }
score'/policy = Policy[path]
```

- Interaction の **優先順位そのものが評価ポリシー選択子**。  
- V82 Priority 表を PE パス分岐に写す。  
- 加点ではなく **どの読み方で評価するか**を選ぶ。

### ④ Rank Swap

```text
ranks' = BaseRanks
FOR horse IN TopN(Base):
    optionally swap / micro-reorder by Interaction strength
# TopN 外は不动
```

- **TopN のみ**相対順位を補正。全体スコア空間は触らないか最小限。  
- 購入・表示に効く頭だけ動かす。

### ⑤ Confidence

```text
rank' = BaseRank          # 変更しない
conf' = f(BaseConf, InteractionFire, Priority)
```

- **順位は不変**。確信度・帯・説明強度のみ変更。  
- 購入閾値や表示に間接影響し得るが、順位 Hit 定義とは分離しやすい。

---

## 方式 × Contract ロールの写像（設計）

| Contract Role | Bonus | Gate | Selector | Rank Swap | Confidence |
|---|---|---|---|---|---|
| Must | 大きな w | 成立条件の核 | パス選択の核 | TopN 補正の主信号 | conf 上昇/維持の主信号 |
| Aux | 小さな w | 緩和条件 | タイブレーク | 微補正 | 弱い conf 調整 |
| Forbidden | w=0 強制 | 発火してもパス禁止 | 選択候補から除外 | swap 禁止 | conf 操作禁止 |

**注:** 写像は設計契約。数値 w / N / 閾値は本フェーズで定めない（実装禁止）。

---

## World 適用方針（Integration 設計・Contract 非変更）

| World | Contract Status | Integration 上の扱い |
|---|---|---|
| rank7 | ACTIVE | 五方式の比較対象に含める |
| midhole | ACTIVE（標本注意） | 比較対象。本番接続候補からは一段下げる |
| unsatisfied | Residual | Baseline Interaction のみ。勝ち筋 Selector 化禁止 |
| core | PROVISIONAL | Integration 実験対象外（方式比較の脚注のみ） |

---

## 推奨候補（設計結論・非実装）

V80（加算族 Strategy が Hit 大幅悪化）を踏まえ:

| 順位 | Mode | 理由 |
|---:|---|---|
| **1（Shadow 第一候補）** | **⑤ Confidence** | 順位非変更 → Hit 定義への直接干渉最小。Rollback 容易。Contract 検証と分離可。 |
| **2** | **④ Rank Swap** | 影響を TopN に閉じ込められる。Hit には触れるが全場 Bonus より制御可能。 |
| **3** | **③ Selector** | Contract Priority との意味整合が最も良い。ただしパス分岐は観測・归因が重い。 |
| **4** | **② Gate** | 意味は強いがカバレッジ欠損・評価不能レース増のリスク大。 |
| **5（非推奨）** | **① Bonus** | V80 と同型リスク最大。単体→Interaction に変えても加算族の失敗モードを継承しやすい。 |

**設計上の段階案（将来・別 Decision）:**

```text
Stage-S0: Confidence Shadow（順位固定）で Interaction 発火と conf 相関を見る
Stage-S1: 条件付き Rank Swap Shadow（TopN・Ready World のみ）
Stage-S2: Selector Shadow（归因 2×2 必須・V79 系）
Bonus / 全面 Gate は Stage に入れない（禁止継続推奨）
```

---

## 归因要件（Integration を測るとき）

V79/V80 と同様、将来 Shadow では:

| 固定 | 動かすもの |
|---|---|
| Trigger / World / Contract | Integration Mode のみ（または Mode×ON/OFF） |
| Legacy PE Base | Adapter 出力との差分 |

本フェーズでは归因実験も実装しない。

---

## 関連成果物

- `v83-integration-matrix.md` — 方式比較表  
- `v83-roi-expectation.md` — ROI / 期待効果（仮説）  
- `v83-governance.md`
