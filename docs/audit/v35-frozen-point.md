# Version35 — Frozen Point Analysis（V34 Shadow AB）

**Phase:** V35 PE Dependency Audit  
**Mode:** Research / Audit only  
**Date:** 2026-07-28  
**根拠実験:** V34 WIC Shadow AB（N=335, World changed 54, Hit/Purchase/rank Δ=0）

---

## ④ Frozen Point — なぜ World が変わっても Prediction が変わらなかったか

### 観測（V34）

| 指標 | 結果 |
|------|------|
| World 変更レース数 | 54 |
| Hit / Purchase / rank710 / other miss Δ | **0** |
| Shadow difficulty | unique_n ≈ 51（変化あり） |
| Control difficulty | ~0.5 定数寄り |
| `frozen_pe_pick` | **True（設計）** |

出典: `services/win5-ai/app/research/wic_shadow_ab.py`（Control/Shadow とも SAME frozen PE pick）。

---

## コード経路による説明

### 経路 F1 — AB 実験設計による凍結（直接原因）

```
Control: Production world signals + assigned world + frozen PE pick
Shadow:  WIC reconstruct difficulty + first-match World + SAME frozen PE pick
                              ↓
                    Hit/Purchase 比較は同一 pick
                              ↓
                    World 54件変化でも Hit Δ=0
```

レポート文言（要約）:

> Hit unchanged: PE pick frozen; World reclassification alone does not alter Prediction top pick in this AB

→ V34 は **World→Prediction 因果を測る実験ではなく、World 再分類の非劣性＋WIC カバレッジを測る実験**。ROI proof は `INCONCLUSIVE_FROZEN_PE`。

### 経路 F2 — 本番コードでも World→Rank が非接続（構造原因）

仮に AB で PE pick を解凍しても、現行本番経路では:

```
World (label)
    ↓（Required / Pool を経由して ranking に戻らない）
Score / Rank は既に確定
    ↓
predict_ranking が world を落とす
    ↓
mapper evaluation.world = None
    ↓
Prediction top pick = Ranker 出力（World 非入力）
```

つまり **構造的 Frozen Point** は:

```
World
  ↓（ラベルのみ）
Required / Candidate Pool   ← ranking の上流ではない
  ↓
PE Top Pick（= Ranker top）← World 非参照で固定
  ↓
Prediction 不変
```

### 経路 F3 — difficulty / WIC 信号の位置

V33/V34 で再構成される `race_leg_difficulty` 等は:

- Production Feature 経路では STABLE default 0.5 に寄りやすい（V30/V31）
- Shadow では FeatureLoader frame から WIC 再構成 → **World 分類入力としては変化**
- しかし Scorer が WIC を **再スコア入力として読まない**限り、top pick は動かない

```
WIC difficulty 変化
  → Shadow World ラベル変化（54 races）
  → Scorer/Ranker 再実行なし / PE pick 凍結
  → Hit 不変
```

---

## Frozen Point 一覧

| ID | 箇所 | 種別 | Prediction への効果 |
|----|------|------|---------------------|
| FP-AB | `frozen_pe_pick=True` | 実験設計 | Hit 比較を強制同一 |
| FP-ORDER | World が Rank **後** | パイプライン順序 | World が score を変えられない |
| FP-SCORER | Scorer に world なし | 欠落接続 | 同上 |
| FP-FACADE | `predict_ranking` が world 省略 | 契約ドロップ | 公開 Prediction が World 非依存 |
| FP-MAPPER | `evaluation.world=None` | 契約ドロップ | UI/評価側も切断 |
| FP-POOL | Pool は post-score | 境界 | Pool 変化≠Hit 変化 |

---

## 結論（本節）

V34 の「World 54 変更・Hit 0」は **偶然ではなく二重凍結**:

1. **実験:** PE pick 明示凍結  
2. **実装:** World が PE ranking の入力契約に入っていない  

→ World 変更が Prediction に伝播しないことは、現行コード経路と整合する。
