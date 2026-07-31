# V51 — Governance（ADR-050 Impact）

**Date:** 2026-07-28  
**Subject:** ADR-050（Canonical = CorePublicBundle）適用時の影響ガバナンス判定  
**Method:** Producer/Consumer 全洗い出し（V51 Impact + Consumer Matrix + Migration）

---

## Scale Definitions

| Grade | Meaning |
|---|---|
| **A 影響限定** | 単一モジュールまたは Research のみ。Product HTTP/GUI 非波及 |
| **B 中程度** | 複数 Platform 層（Single/Facade/Mapper）だが Client 契約は維持可能 |
| **C 広範囲** | Product Public（HTTP + GUI + Functions + Conversation 等）に波及し、契約二重化の解消が横断的 |

---

## Verdict

# **C — 広範囲**

---

## Evidence

### 1. Public surface が広い

| Surface | Contract today | ADR-050 実装時 |
|---|---|---|
| win5-ai `/v1/predictions*` | PredictionBundle | 変更必須 or Dual |
| Cloudflare Functions adapter | Bundle proxy / Ready | 変更必須 |
| GUI `prediction.js` + ContractGuard | Bundle 2.0 | 変更必須 |
| Conversation / Challenge | Bundle | 変更必須（間接） |
| Single API / CLI / Eval | predict_* → Bundle 系 | 入口変更必須 |

→ Product 面だけで **5系統以上** が同時影響。

### 2. スキーマ非互換

CorePublicBundle ≠ PredictionBundle。  
単純な「入口差し替え」では Client が壊れる。View Adapter + Dual-publish が必須 → 影響は **横断設計**。

### 3. 欠陥の性質が契約層

`evaluation.world = None` は PE/World バグではなく **View/Mapper 契約欠陥**（ADR-050）。  
修正対象が「公開契約の定義」であるため、Governance は World ロジック変更（別トラック）より **公開面の広さ** で C。

### 4. 非影響領域があっても Grade は下がらない

| 非影響 | 理由 |
|---|---|
| PE Feature/Scorer/Ranker | Bundle 非関与 |
| Win5 Optimizer / Trigger | CE 非呼び出し |
| Research CE 利用者 | 既に Canonical 寄り |

非影響があっても、**変更必須 Consumer の数と Public 破壊リスク**が C 条件を満たす。

### 5. Rollback が多段必須

R1 Dual → R2 View Adapter → R3 Client Guard。  
単一 PR での完結が危険 = 広範囲ガバナンス。

---

## Why not A / B

| Grade | Reject reason |
|---|---|
| A | HTTP/GUI/Functions が対象外ではない |
| B | 「Mapper だけ直せば Client 維持」は不十分。Guard・Ready・Mock・Conversation が連動 |

---

## Implications（実装しない前提の方針）

1. **一括 Hard cutover 禁止**（R5 相当は別 ADR）  
2. **PredictionBundle を即廃止しない**（Product View 維持）  
3. **PE / World / Trigger / Signal / Production を契約移行の言い訳で触らない**  
4. 次フェーズ候補は **Shadow / Dual-publish 設計** のみ（実装は Decision 後）  
5. Client Contract 変更は **Server 変更と同一ゲート** で扱う

---

## Relation to prior Governance

| Phase | Topic | Grade |
|---|---|---|
| V47 | PE Responsibility 混在 | C |
| V48 | CE 契約に world 残存 vs Prediction drop | C |
| V49 | Prediction 契約二重化 | C |
| V50 | ADR-050 Accepted（設計） | — |
| **V51** | **ADR-050 実装影響範囲** | **C** |

一貫して **契約層の構造問題**。V51 は「直す範囲が Product 全域に広がる」ことを確定。

---

## Decision Gate（参照）

```
【Decision】※本フェーズは分析のみ
Action Type: Architecture Impact Audit
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No（差分なし）
Risk: Documented High on Public surfaces if implemented without Dual/View
Expected Next Action: Migration design (Shadow/Dual) under new Decision — not implement yet
```

---

*V51 Governance — research only. Grade C.*
