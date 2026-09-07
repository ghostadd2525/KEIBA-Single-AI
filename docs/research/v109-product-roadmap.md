# Version109 — Product Roadmap（Consumer Development）

**Date:** 2026-07-28  
**Status:** Active Program · Core Research **CLOSED**  
**Parents:** V108 READY_WITH_CONDITIONS · ADR-009 · ADR-010 · ADR-011（Version1 Platform Contract）  
**非目的:** Core Improvement 研究

---

## 一文

**Version1 Core は安定運用。開発は Single / Win5 Consumer。不足はまず Consumer。Core 改変は例外証明または Version2 正式開始のみ。**

---

## 1. プログラム状態

| 領域 | 状態 |
|---|---|
| Core Platform Version1 | **FROZEN · 安定運用優先**（V108 READY_WITH_CONDITIONS） |
| Core Improvement（V1 名義） | **禁止** |
| Version2 Platform Research | **未開始**（開始は別 Gate）· 目的ロック: `v2-platform-research-purpose.md`（昇格研究ではない） |
| PROMOTE 配線 | **別 Gate のみ**（serialize。意味変更なし） |
| Single AI Consumer | **開発対象** |
| Win5 AI Consumer | **開発対象**（Single 基礎の後追い可） |

---

## 2. Version1 Platform Contract（固定）

| ADR | 役割 | Version1 での扱い |
|---|---|---|
| ADR-009 | Core Completeness | **固定** |
| ADR-010 | Explanation Confidence | **固定** |
| ADR-011 | Product Integration | **固定**（Consumer 実装は契約内） |

索引: `docs/adr/PLATFORM-V1-CONTRACT.md`

---

## 3. 開発トラック

### Track S — Single AI（優先）

| 順 | 成果 | 依存 |
|---|---|---|
| S0 | Decision Registry（V88/V95 表のコード化・読取） | Core read-only |
| S1 | Consumer API `consumer-api/single/v1`（構造化） | S0 |
| S2 | Presentation（structured → optional NL） | S1; CORE_V103 は別 Gate |
| S3 | Ticket Policy（ADR-008 Flag 連動） | S1; `W_DECISION_*` |
| S4 | Staging Flag / Shadow 対照 | S2–S3 |

### Track W — Win5 AI

| 順 | 成果 | 依存 |
|---|---|---|
| W0 | Consumer API `consumer-api/win5/v1` 骨格 | S1 安定推奨 |
| W1 | Candidate Expansion（V92 Pool 表） | W0 |
| W2 | Coverage Strategy | W1 |
| W3 | Race Selection（KEEP_DERIVED・difficulty 非新設） | W0–W2 |
| W4 | Staging / Canary | W1–W3 |

### Track P — PROMOTE Wiring（別 Gate）

| 順 | 成果 | 制約 |
|---|---|---|
| P1 | V103 PROMOTE Shadow serialize | Logic/意味変更禁止 |
| P2 | `W_CORE_PAYLOAD_V103` staging | Consumer と归因分離可 |

**Track P は Core Improvement ではない。** serialize のみ。

---

## 4. マイルストーン

| Milestone | 定義 | 出口 |
|---|---|---|
| M-Consumer-0 | 本 Roadmap + Architecture 文書 | 本 V109 |
| M-Single-Alpha | Registry + Single Consumer API + Presentation（Flag OFF 可） | Shadow レポート |
| M-Single-Beta | Ticket Policy + Decision Flag staging | Rank 非劣化ゲート |
| M-Win5-Alpha | Candidate + Coverage Shadow | V106 W-CC 準拠 |
| M-Win5-Beta | Race Selection + staging | Canary 準備 |
| M-PROMOTE | 別 Gate 承認後のみ | fingerprint 再現 |

---

## 5. Core 変更が許される場合（限定）

| # | 条件 | 扱い |
|---|---|---|
| 1 | **Contract Violation**（Consumer 修復不能が証明） | Version1 緊急修復 Gate |
| 2 | **Semantic Gap**（GAP-SEM > 0 再現証明） | 同上 |
| 3 | **Backward Compatibility Failure**（構造破綻の証明） | 同上 |
| 4 | **Version2 Platform Research の正式開始** | V1 と分離した次世代プログラム。V1 安定運用を黙って壊さない |

不足・要望のみでは Core を変えない。順序は常に:

1. Consumer / Registry / Presentation / Ticket / EXT  
2. 例外 1–3 の証明  
3. または Version2 正式キックオフ  

---

## 6. 禁止バックログ（Version1 で受け付けない）

- Core Improvement を目的とした変更・研究  
- 新 World / 新 Affinity 定義 / EC 再定義（V1 名義）  
- Evidence 混線による Core KPI 変更  
- Prediction / Ranking / Score / Trigger 改善を目的とした研究  
- 「Version2 のつもり」で V1 Core を無断改変  

---

## Related

- `v109-single-architecture.md`
- `v109-win5-architecture.md`
- `v109-consumer-api-integration.md`
- `v109-migration-plan.md`
- `v109-governance.md`
- `v110-prediction-completeness-charter.md`（解釈 A）
- `v2-platform-research-purpose.md`（V2 目的ロック · 未開始）
- `../adr/PLATFORM-V1-CONTRACT.md`
