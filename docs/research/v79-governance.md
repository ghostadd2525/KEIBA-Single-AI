# Version79 — Governance（Pilot Attribution Design）

**Date:** 2026-07-28  
**Verdict:** **A（归因可能な Pilot/Shadow 構成を定義）**  
**Type:** Design only  
**Locks:** 実装禁止 / PE 変更禁止 / Production 変更禁止 / 改善禁止

---

## 判定理由

1. V78 の CEW→Pilot PE 単アームは Δ_Trigger と Δ_Strategy を交絡させる。  
2. V79 で 2×2（LL/CL/CP/LP）と Δ オペレータを定義し、一意归因ルールを固定した。  
3. Shadow は Production 非干渉の並列セル評価として設計。  
4. コード・PE・Production は未変更。

---

【Decision】

| Item | Value |
|---|---|
| Action Type | Pilot Attribution Design |
| Implementation Required | **No** |
| Deployment Required | No |
| Configuration Required | No |
| Production Required | No |
| Rollback Required | No |
| Risk | None（文書のみ） |
| Expected Next Action | 別 Decision で ATTR-FULL Shadow 評価（実装）。V78 Production Pilot ON は归因 Shadow 後が望ましい |

---

## 成果物

| Doc | 内容 |
|---|---|
| `v79-pilot-attribution-design.md` | ①②③ + 直交因子 |
| `v79-attribution-matrix.md` | ④ Matrix |
| `v79-shadow-configuration.md` | ⑤ Shadow |
| `v79-governance.md` | 本ファイル |

---

## 遵守

| 制約 | |
|---|---|
| 実装禁止 | PASS |
| PE/Production 変更禁止 | PASS |
| 改善禁止 | PASS |
| 归因一意性の設計 | PASS |

---

## 硬制約（継続）

- LL+CP のみの結果で「Trigger が効いた」「Strategy が効いた」と断言することを **禁止**  
- Attribution 未完了のまま Production で CEW∧Pilot を ON にすることを **非推奨**  
