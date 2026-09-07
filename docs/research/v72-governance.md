# Version72 — Governance（Intent Ground Truth Redefinition）

**Date:** 2026-07-28  
**Verdict:** **A（CEW 定義完了 — 契約正本化）**  
**Type:** Design Definition only  
**Locks:** Trigger / Blueprint 実装 / Signal / Threshold / PE / Prediction / Production — **未変更**

---

## 判定理由

1. V71 により V65 Intent GT は V43/V44/V69 と非同一と確定。  
2. V72 は Intent GT を **Semantic → Trigger Contract → Expected World** で再定義し、正本を V43/V44 に固定。  
3. winner_rank / 人気 / score を Label 定義から排除。  
4. 実装・Trigger 変更なし（定義文書のみ）。

---

【Decision】

| Item | Value |
|---|---|
| Action Type | Intent GT Redefinition（CEW） |
| Implementation Required | **No**（本フェーズ） |
| Deployment Required | No |
| Configuration Required | No |
| Production Required | No |
| Rollback Required | No（V65 は歴史記録として残置可） |
| Risk | Low（文書のみ） |
| Expected Next Action | 別フェーズで CEW に基づく 285R 再評価（実装は別 Decision）／V70 Soft は引き続き HOLD |

---

## 正本・廃止

| 項目 | 状態 |
|---|---|
| Intent GT 正本 | **V72 CEW**（本ドキュメント群） |
| V65 Intent GT | 設計評価用途 **廃止** |
| V43 / V44 | 意味・Trigger 契約の唯一正本（変更なし） |
| V69 Blueprint | 被評価設計（GT ではない） |

---

## 成果物チェック

| # | Doc | Status |
|---|---|---|
| ① | `v72-ground-truth-definition.md` | Done |
| ② | `v72-world-label-rule.md` | Done |
| ③ | `v72-intent-label-guideline.md` | Done |
| ④ | `v72-evaluation-protocol.md` | Done |
| ⑤ | `v72-governance.md` | Done |

---

## 遵守確認

| 制約 | |
|---|---|
| Trigger 非変更 | PASS |
| Blueprint 非変更 | PASS |
| Signal / Threshold 非変更 | PASS |
| PE / Prediction / Production 非変更 | PASS |
| 実装禁止 | PASS |
| winner_rank ベース GT 禁止 | PASS |
| V43/V44 のみから導出 | PASS |

---

## 次にやってはいけないこと

- 本定義を待たず V65 Acc で Soft/Cutover 判定すること  
- CEW を実装する名目で Trigger / Threshold を書き換えること（別 Decision 必須）  
- CEW を Shadow 出力のコピーで代替すること（循環）  
