# Platform Version1 Contract（固定索引）

**Status:** FROZEN · **安定運用優先**  
**Date:** 2026-07-28（追記: 2026-07-29）  
**Authority:** V108 Platform Readiness · V109 Consumer Development  
**Verdict context:** READY_WITH_CONDITIONS（配線は Consumer / PROMOTE Gate）

> **2026-07-29:** Single AI Version1 **開発完了** · **運用管理フェーズ**へ移行。  
> 新規機能停止。`single_ai_detail` OFF 維持。恒久 Cutover は別 Gate。  
> 正本: `docs/research/v109-single-ai-v1-development-complete.md`

---

## 構成 ADR（Version1 期間は改訂禁止）

| ADR | Title | Path |
|---|---|---|
| **ADR-009** | AI Core Completeness | `docs/adr/ADR-009-ai-core-completeness.md` |
| **ADR-010** | Explanation Confidence | `docs/adr/ADR-010-explanation-confidence.md` |
| **ADR-011** | Product Integration | `docs/adr/ADR-011-product-integration.md` |

補助（Version1 で意味変更しない）: ADR-003 · ADR-008 · V103/V105/V106/V107/V108

---

## Version1 方針

| 方針 | 内容 |
|---|---|
| 開発対象 | **Single AI / Win5 AI / Consumer**（Core ではない） |
| Core | **安定運用優先**。Improvement を目的とした変更は行わない |
| 不足時 | **まず Consumer**（Registry / Presentation / Ticket / EXT）で解決可能か検討 |
| PROMOTE | serialize 配線のみ **別 Gate**（意味・Logic 変更を含まない） |

---

## Core 変更禁止一覧（Version1）

Prediction · Ranking · Score · Trigger · World · Near Miss · Affinity · Explanation Confidence · Evidence · Contract

---

## Core を変更できる場合（限定）

次のいずれかが満たされたときのみ:

| # | 条件 | 説明 |
|---|---|---|
| 1 | **Contract Violation** | ADR-009/010/011 と矛盾し、Consumer では修復不能であることが証明された |
| 2 | **Semantic Gap** | GAP-SEM > 0 が再監査で再現証明された |
| 3 | **Backward Compatibility Failure** | 版規則下でも Consumer Contract が構造的に破れることが証明された |
| 4 | **Version2 Platform Research の正式開始** | 別プログラムとして宣言・Gate 承認された場合のみ。Version1 Core の安定運用経路とは分離する |

1–3 は **緊急修復**。4 は **次世代研究**であり、Version1 本番契約を黙って書き換えない（併存・分岐・明示的移行が必須）。

---

## Version1 開発対象

- **Single AI:** Consumer API · Decision Registry · Presentation · Ticket Policy  
- **Win5 AI:** Consumer API · Candidate Expansion · Coverage · Race Selection  

Core Improvement 研究（Version1 名義）は **受付終了**。  
Version2 研究は **未開始**（開始時は専用 Gate / 文書が必要）。

---

## Version2 との分離（方針ロック · 2026-07-29）

| 項目 | 内容 |
|---|---|
| Version1 Completeness | 解釈 A: Prediction Returned=100% · `unsatisfied` 許容 · NM/Affinity **昇格禁止**（`v110-prediction-completeness-charter.md`） |
| Version2 目的（開始前ロック） | `unsatisfied` が現行 World 定義の限界か、新 World 構造で自然分類可能かの **Theory 検証**（`v2-platform-research-purpose.md`） |
| Version2 非目的 | Affinity による Positive World **昇格**を研究目的としない |
| 混線 | V1 契約・KPI・本番経路に V2 仮説を混ぜない |

ADR-009 / ADR-010 / ADR-011 は Version1 期間 **改訂しない**。

---

## 関連

- `docs/research/v109-product-roadmap.md`
- `docs/research/v109-governance.md`
- `docs/research/v110-prediction-completeness-charter.md`
- `docs/research/v2-platform-research-purpose.md`
