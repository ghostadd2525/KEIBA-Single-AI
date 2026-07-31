# Version110 — Prediction Completeness（解釈 A · 確定）

**Date:** 2026-07-29  
**Status:** **ADOPTED — Interpretation A** · Version1 Platform Contract **維持**  
**Parents:** ADR-009 · ADR-010 · ADR-011 · PLATFORM-V1-CONTRACT  
**ADR 改訂:** **なし**（009/010/011 非変更）  
**Version2:** 本票とは **完全分離**（目的定義のみ別文書。正式開始は未）

---

## 採用決定

| 項目 | 決定 |
|---|---|
| 解釈 | **A** |
| Prediction Returned | **100%** |
| World = `unsatisfied` | **許容**（所属ラベルとして有効） |
| Near Miss / Affinity 自動昇格 | **禁止** |
| ADR-009 / 010 / 011 | **変更しない** |
| PLATFORM-V1 | **維持** |
| ROI / Ticket / Decision | **評価対象外** |

---

## 1. Version1 目的（本票の範囲）

全レースで **Prediction（Rank/Score）を返す**。

| 概念 | V1 での役割 |
|---|---|
| Prediction | **全レース返却必須**。`unsatisfied` / Near Miss / Residual を理由に withhold **しない** |
| World | 契約どおりのラベル。**`unsatisfied` を含む** |
| Near Miss / Affinity / Residual | Completeness **観測**（説明・分類）。**昇格ルールではない** |
| Unassigned (V1) | `world_id` **欠損**のみ。`unsatisfied` は Unassigned **ではない** |

目標指標（V1 定義）:

| ID | 指標 | 目標 |
|---|---|---|
| PR-100 | Prediction Returned | **1.0** |
| PC-C | Prediction Coverage（Rank/Score） | **1.0** |
| WC-C | World Coverage（label · unsatisfied 含む） | **1.0** |
| UA-0 | Unassigned（`world_id` null） | **0** |

詳細: `v110-metric-contract.md`

---

## 2. Version1 でやること / やらないこと

### やる（V1 · Core 意味非変更）

- Prediction Returned ギャップの観測・運用修復（readiness / Bundle 供給 / 404 経路）
- NM を Prediction 失敗理由にしないことの明示（仕様・文書・回帰）
- Completeness レポートを V1 定義で継続

### やらない（V1）

- Affinity / near_world による CEW 書き換え
- Near Miss の Positive World 昇格
- `unsatisfied` 削減を KPI 化
- ADR-009/010/011 の改訂
- Version2 World Theory の実装混入

---

## 3. Version2 との分離（必須）

| | Version1（本票） | Version2 |
|---|---|---|
| 状態 | **現行契約 · 運用** | **未開始**（正式 Gate 後のみ） |
| 目的 | Prediction Returned 100% · Completeness | World Theory 検証（下記） |
| `unsatisfied` | **許容** | 研究対象（限界か新構造か） |
| NM / Affinity | 昇格禁止 · 観測 | **昇格ルールにしない** · Theory 検証の観測 |
| コード/契約 | PLATFORM-V1 | 別プログラム · 別文書 · 併存必須 |

Version2 の研究目的は **「Affinity による Positive World 昇格」ではない。**

正規定義: `v2-platform-research-purpose.md`（正式開始前の目的ロック。実装 Gate ではない）

---

## 4. Decision

```
【Production Diagnosis】
解釈 A 採用。V1 Contract 維持。Prediction Returned=100%。昇格禁止。

【Server Diagnosis】
Status: PASS（方針確定）
Evidence: ユーザー明示採用 · ADR 非改訂 · V2 分離宣言

【Client Diagnosis】
Status: BLOCKED
Client Evidence: 方針ロック段階。サイト検証は後続 Track

Diff Summary: V110 を解釈 A に確定。V2 目的を昇格から World Theory 検証へ再定義（未開始）。
Root Cause: N/A（方針決定）
Expected Action: V1 は PR-100 ギャップ Track。V2 は目的文書のみ・実装禁止

【Decision】
Action Type: Policy Lock (Interpretation A)
Implementation Required: No（Core/World/ADR 変更なし）
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: Low（V1 維持）
Expected Next Action: V1 Prediction Returned gap inventory（観測のみ可）
```

---

## Related

- `v110-metric-contract.md`
- `v110-v1-prediction-returned-track.md`
- `v110-governance.md`
- `v2-platform-research-purpose.md`
- `PLATFORM-V1-CONTRACT.md`
