# V53 — Governance（Prediction Assembly Boundary）

**Date:** 2026-07-28  
**Subject:** Is Prediction Assembly the correct AI Core ↔ Product boundary?  
**Method:** Ownership + input/output + leak audit against live code (V50–V52 + V53)

---

## Scale Definitions

| Grade | Meaning |
|---|---|
| **A** | Assembly が適切な責務境界 — 層定義がコード契約と一致し、主要 Leak なし |
| **B** | 一部責務混在 — 境界種は正しいが、所有・入力・実装分散に混在あり |
| **C** | Assembly では責務分離できない — 多ソース合成でも層を划れない |

---

## Verdict

# **B — 一部責務混在**

---

## Why Assembly is still the right *kind* of boundary

| Argument | Evidence |
|---|---|
| Core に置けない | Facade: no Product-stage; no Bundle/Bet in CorePipeline |
| Presentation に置けない | GUI は Bundle Consumer; RaceData/Bet 非呼び出し |
| 単純 View では足りない | V52: race_info + betting_recommendations が CE 外 |
| Bet は Product 合成 | BetBuilder: Plan only; no CE; BetStrategy: no re-rank |
| RaceInfo は RaceData 所有 | Mapper `_race_info` + `get_race` |

→ 多ソース合成点としての **Assembly 境界は成立する**（C を否定）。

---

## Why not A

| Mixing | Evidence |
|---|---|
| Core 事実の破棄 | Mapper `evaluation.world/sub_world = None` |
| Canonical 未接続 | Assembly が `evaluate_candidates` ではなく compatibility views |
| 境界モジュール不在 | predict + models + mapper + adapter + mock に分散 |
| Explain 二重 | Core `explain_payload` vs Mapper Bundle explain |
| Catalog/Mock 並列 Assembly | Core を通らない同一 Adapter 出口 |
| Product が Bundle を事実上 Canonical 扱い | HTTP 共通契約コメント vs ADR-050 |

これらは「Assembly という層が間違っている」ではなく、**現行 Assembly 相当コードの混在**。

---

## Why not C

責務は Owner 表で分離可能:

- AI Core: Rank, Confidence, World, SubWorld, Meta  
- RaceData/Catalog: RaceInfo, Catalog  
- Product Bet: BettingRecommendations  
- Assembly: compose + ChallengeMark overlay + DTO  
- Presentation: render  

分離不能の証拠は無い。欠陥は遵守違反と分散。

---

## Leak → Governance mapping

| Leak | Affects grade |
|---|---|
| world=None | blocks A |
| CE not Assembly input | blocks A |
| Scattered modules | blocks A |
| Core に Bet なし / GUI 非合成 | supports not-C / partial A |

---

## Implications（実装しない）

1. ADR-050 移行の次設計単位は **Pure View Adapter ではなく Assembly Boundary**（V52 と整合）。  
2. Assembly を正式境界にするなら、設計上の必須条件は:
   - Canonical CE（または等価で World 保持する入力）を組み立て入力に含む  
   - Core 所有フィールドを破棄しない  
   - RaceData / Bet / Catalog を明示 Input Contract に列挙  
3. 現状の分散実装を「境界が無い」と誤読しない — **種は正しく、形が未整備**。  
4. **コード変更は本フェーズ外**。

---

## Decision Gate（参照）

```
【Decision】※分析のみ
Action Type: Prediction Assembly Boundary Audit
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: Medium if Assembly charter skipped and Mapper treated as Canonical
Expected Next Action: Design-only Assembly Charter / Input Contract freeze (optional next research) — no implementation
```

---

## Grade chain

| Phase | Topic | Grade |
|---|---|---|
| V50 | Canonical = CorePublicBundle | ADR Accepted |
| V51 | Impact of adopting ADR | C（広範囲） |
| V52 | View Adapter alone | C（成立しない） |
| **V53** | **Assembly as Core↔Product boundary** | **B（境界種は正しい／一部混在）** |

---

*V53 Governance — research only. Grade B.*
