# Version7/8 Architecture Review（ADR-009/010 照合）

**Date:** 2026-07-28  
**Mode:** Audit only · 推測禁止 · 根拠はコード/ADR/設計資料のみ  
**照合先:** ADR-009（Core Completeness）· ADR-010（Explanation Confidence）· V103 Contract Surface

---

## 監査スコープの定義（必須）

本リポジトリには **二つの「Version 7/8」表記**がある。混同を避けるため分離する。

| スコープ | 範囲 | 主な根拠 |
|---|---|---|
| **A. Product Version7–8** | `docs/ops/v7-*`, `docs/ops/v8-*`, `docs/baselines/Version8.5*.md`, ResultAutomation | 運用ベースライン 8.5 / 自己改善サイクル |
| **B. Research Version70–89** | `docs/research/v70`–`v89`, ADR-008 準備 | World/CEW/Decision 研究（番号が 7x/8x） |

ADR-009/010 が直接参照する Near Miss Taxonomy / Affinity / Explanation Confidence は **Research V94–V101** で確定しており、**Product V7–V8 文書には用語として現れない**（下記 Gap）。

本レビューは **A を主対象**とし、B は「同番号帯の研究」として併記する。

---

## 総括（先に結論）

| 問い | Product V7–V8 | Research V70–V89 |
|---|---|---|
| Evidence 蓄積で AI が成長する設計 | **ある**（ただし Prediction Miss 改善用） | World Evidence 棚卸し（V76）あり。Affinity/Near Miss 成長層は **なし** |
| World/Near Miss/Affinity/Explanation を Evidence で育てる設計 | **根拠なし** | Near Miss/Affinity は V70–V89 範囲外（V94+） |
| Semantic 固定し Evidence のみ増やす | PE/CE 凍結は **ある**。World 意味の固定は **Product V8 主文書にない** | V72–V75 Contract 固定思想 **あり** |
| Prediction / Decision / Betting 分離 | Prediction 凍結・読取分離 **あり**。Ticket Decision Layer / Betting **なし**（V8 の Decision≠券種） | V88–V89 で Decision Layer **設計出現**。Betting 最適化は V93 |

---

## ① Evidence Layer

### Product V7–V8 — 存在（別目的）

**設計:** `docs/ops/v8-self-improvement-cycle.md`

> Production（土日）: ResultAutomation → Evidence → Archive  
> Research（月〜金）: Evidence → Analyzer → Proposal → Canary → 285R  
> Non-goals: Prediction Engine / Candidate Evaluation / AI ロジックの直接変更

**コード:**

- `services/win5-ai/app/ops/state_machine.py` — 状態 `EVIDENCE_EXPORTING`
- `services/win5-ai/app/ops/result_automation.py` — Miss JSON を `evidence/improvement` へ書込み、`improvement_evidence_index` に索引

```1371:1395:C:\win5-ai\KEIBA-Single-AI\services\win5-ai\app\ops\result_automation.py
            dest = imp_root / et / race_date / f"{race_id}.json"
            atomic_write_json(dest, env)
            ...
                INSERT OR REPLACE INTO improvement_evidence_index(
                  event_id, event_type, race_id, race_date, fingerprint,
                  path, run_id, created_at
                ) VALUES (?,?,?,?,?,?,?,?)
```

Miss 抽出条件（Hit 失敗）:

```1420:1428:C:\win5-ai\KEIBA-Single-AI\services\win5-ai\app\ops\result_automation.py
            FROM race_evaluations e
            ...
            WHERE e.race_date=? AND e.hit_at_1=0
```

**Baseline:** `docs/baselines/Version8.5.md` — 土日 Production で Miss → Archive、月〜金 Research。

**ADR-009 との差:** Product Evidence は **Prediction Miss（hit_at_1=0）** の統計・再現用。  
World / Near Miss / Affinity / Explanation Completeness を蓄積して Core を成長させる層としては **文書・コードとも根拠なし**。

### Research V70–V89 — 部分的

- `docs/research/v76-world-evidence.md` — World Ready に必要な **証拠不足の棚卸し**（実装禁止）。観測・分割再現の欠落を列挙。  
  → 「Evidence Layer として Affinity/Near Miss を貯めて成長」ではなく **Readiness 監査**。
- Near Miss / Affinity の Evidence 成長設計は **V94–V96 以降**（本スコープ外）。

---

## ② Semantic Layer の固定

### Product V7–V8

| 根拠 | 内容 |
|---|---|
| `v8-operations-baseline.md` / `Version8.5.md` | PE / CE / AI / Production ロジック変更 **禁止**（意味の「凍結運用」） |
| ADR-003 | Prediction 読取専用・Conversation 非改変 |

**World / Near Miss / Contract 意味の固定**を Product V8 主系が宣言した根拠は **見つからない**。  
（World 意味契約は `docs/architecture/v32-world-adr.md`, `v43-world-semantic-contract.md`, Research `v75-world-strategy-contract.md` — Product Version8 ベースライン文書からは独立）

### Research V70–V89 — 存在

| 根拠 | 内容 |
|---|---|
| `v72-world-label-rule.md` / `v73-contract-intent-evaluation.md` | CEW ラベル規則・意図評価 |
| `v75-world-strategy-contract.md` | World Strategy MUST/MUST NOT 固定。C5: Trigger/CEW 変更しない |
| `v75` C4 | Hit/Purchase を適合判定に使わない |

→ ADR-009 の「意味を固定し観測で測る」に **近い思想は Research V72–V75 に存在**。  
Product V8 の「PE 凍結＋Miss Evidence」とは **別系統**。

---

## ③ Decision Layer 分離

### Product V7–V8

| 用語 | 根拠上の意味 | ADR-008/009 の Decision との関係 |
|---|---|---|
| **Decision**（金曜） | Analyzer→…→**Accept/Reject/no_improvement**（`v8-operations-baseline.md` Decision Rule） | **異なる**。券種・Skip・資金ではない |
| Prediction 分離 | ADR-003; V8 Non-goals で PE 直接変更禁止 | **一致方向**（読取・非改変） |
| Betting | Product V8 主文書に Ticket Betting Layer の設計 **なし** | ADR-009 の Betting=Decision 外は **後続（V93）** |

### Research V70–V89 — Decision Layer 出現

| 根拠 | 内容 |
|---|---|
| `v88-decision-policy.md` | Prediction 後の Decision Layer（Ticket/Risk/Pool/Explanation）設計のみ |
| `v89-decision-shadow.md` | Shadow 評価 |
| ADR-008（V90） | Decision Layer 正式 ADR |

→ Prediction/Decision **分離思想は V88 で明確化**。Product V8 の「Decision」語とは **同名異義**。

---

## ④ 現行 ADR との差分（要約表）

詳細は `v7v8-adr-mapping.md` / `v7v8-gap-analysis.md`。

| 概念 | Product V7–V8 | Research V70–V89 | ADR-009/010 / V103 |
|---|---|---|---|
| Evidence 蓄積 | Miss Evidence **実現済み** | World Evidence 棚卸し | Completeness/EC 観測へ **再設計・拡張** |
| World 意味固定 | 非主対象 | Contract **実現（設計）** | Completeness KPI に **再配置** |
| Near Miss / Affinity | **なし** | **なし**（V94+） | **追加** |
| Explanation Confidence | **なし**（Prediction Confidence 文脈は Conversation） | V84 は Calibration Confidence | ADR-010 で **再定義・追加** |
| Ticket Decision Layer | **なし** | V88–V91 **設計→Shadow** | ADR-008 維持、Core 外 |
| Betting 最適化 | **なし** | V93 | Core KPI 外（ADR-009） |

---

## 成果物一覧

| 成果物 | Path |
|---|---|
| Architecture Review | 本ファイル |
| Evidence Layer Audit | `docs/research/v7v8-evidence-layer-audit.md` |
| ADR Mapping | `docs/research/v7v8-adr-mapping.md` |
| Gap Analysis | `docs/research/v7v8-gap-analysis.md` |
| Governance | `docs/research/v7v8-governance.md` |
