# Version105 — Evidence Taxonomy

**Date:** 2026-07-28  
**Status:** Design only · **実装禁止**  
**Parents:** ADR-003 · ADR-008 · ADR-009 · ADR-010 · V8 Self-Improvement Cycle · V92 Evidence Platform · V103 Contract Surface · V7/V8 Evidence Audit  
**目的:** Product Evidence と Core Evidence を統合管理し、**Prediction 改善**と **Semantic 蓄積**を混同しない。

---

## 一文

**Evidence は一つではない。Prediction / Semantic / Decision の三系統であり、経路・KPI・昇格先を共有してはならない。**

---

## 1. 上位区分（必須）

| Plane | 別名 | 目的 | 非目的 |
|---|---|---|---|
| **Product Evidence** | 本番観測パイプライン | レース結果後の事実・Miss・Archive（V8） | Core 意味の成長・Completeness KPI |
| **Core Evidence** | Semantic / Completeness 観測 | World / Near Miss / Affinity / EC の記述完全性（ADR-009/010） | Hit 改善・ROI・券種 |

統合管理 = **カタログと境界規則を一つにする**こと。  
**ストア・スキーマ・KPI を一つに混ぜることではない。**

---

## 2. 三分類（本票の正規 Taxonomy）

```text
┌─────────────────────┐
│ Prediction Evidence │  ← Product Miss / Snapshot / Hit 評価
└──────────┬──────────┘
           │ 混線禁止
┌──────────▼──────────┐
│ Semantic Evidence   │  ← Core Completeness / World / NM / Affinity / EC
└──────────┬──────────┘
           │ 混線禁止
┌──────────▼──────────┐
│ Decision Evidence   │  ← Ticket / Skip / Betting / ROI Shadow
└─────────────────────┘
```

| Class ID | 名称 | 定義（何の証拠か） | 祖先根拠 |
|---|---|---|---|
| **EV-P** | **Prediction Evidence** | Rank/Score の付与・Hit/Miss・予測時点 Snapshot に関する観測 | V8 Miss Evidence; V92 Prediction Snapshot; ADR-009 Prediction Completeness |
| **EV-S** | **Semantic Evidence** | World / Near Miss / Affinity / Transition / Exclusion / Explanation Confidence の記述・充足・一貫性 | ADR-009; ADR-010; V75 Contract; V76 World Evidence; V95–V96; V103 PROMOTE |
| **EV-D** | **Decision Evidence** | Ticket / Pool / Risk / Skip / Betting / ROI Pattern の Shadow・採否・PnL 観測 | ADR-008; V88–V93; V97–V98 |

---

## 3. 種別カタログ（Sub-types）

### 3.1 Prediction Evidence（EV-P）

| Sub-ID | 名称 | 内容 | 既存根拠 |
|---|---|---|---|
| EV-P-MISS | Miss Evidence | `hit_at_1=0` 等の外れイベント JSON | `result_automation.py`; `v8-self-improvement-cycle.md` |
| EV-P-EVAL | Race Evaluation | `race_evaluations` / Hit 指標 | V8 Operations Baseline |
| EV-P-SNAP | Prediction Snapshot | 予測時点の事実（結果後 Miss と分離） | `v92-evidence-platform.md` |
| EV-P-COMP | Prediction Completeness Trace | Rank/Score 欠損・再現性監査 | ADR-009 §4 |

### 3.2 Semantic Evidence（EV-S）

| Sub-ID | 名称 | 内容 | 既存根拠 |
|---|---|---|---|
| EV-S-WORLD | World Label Trace | CEW / MATCH / Exclusion トレース | ADR-009; Trigger/CEW 既存契約 |
| EV-S-NM | Near Miss Record | Near Miss / Pure Residual / near_world / Must Gap | V95; ADR-009 Near Miss Completeness |
| EV-S-AFF | Affinity Vector | must_affinity 等（CEW 非改変） | V96; V103 MS-2 |
| EV-S-EXCL | Exclusion Reasons | 除外理由リスト | V103 MS-3 |
| EV-S-EC | Explanation Confidence Bundle | EC-S/W/N/T | ADR-010; V103 MS-4 |
| EV-S-READY | World Readiness Audit | Ready 証拠欠落の棚卸し | V76（監査型・非 Hit） |

### 3.3 Decision Evidence（EV-D）

| Sub-ID | 名称 | 内容 | 既存根拠 |
|---|---|---|---|
| EV-D-SHADOW | Decision Shadow Run | Ticket/Pool/Risk Shadow 結果 | V89; V91; ADR-008 |
| EV-D-BET | Betting Policy Trial | 券種・stake 実験 | V93 |
| EV-D-ROI | ROI Attribution | Near Miss ROI Pattern 等 | V98 |
| EV-D-AFFVAL | Affinity→Decision Value | Affinity の購入価値検証 | V97（NO_VALUE 記録を含む） |
| EV-D-FRI | Friday Accept/Reject | 改善提案の採否（Product 週次 Decision） | `v8-operations-baseline.md` ※語は Decision だが **EV-P 改善ゲート**（下記注） |

**注（同名異義の固定）:** Product V8 の金曜「Decision」は **EV-P 改善提案の採否**であり、ADR-008 Ticket Decision Layer ではない（`v7v8-adr-mapping.md`）。本 Taxonomy では採否ログを **EV-D-FRI** に置き、**EV-D-SHADOW 系と混同しない**（Owner が異なる）。

---

## 4. 混同禁止マトリクス（MUST）

| From ↓ / To → | EV-P | EV-S | EV-D |
|---|---|---|---|
| **EV-P を使ってよい用途** | Analyzer / Proposal / Canary / Hit 研究 | **禁止**（Miss 件数で World 意味を変えない） | 読取のみ可（購入最適化の入力に Rank を使うのは Decision 側契約に従う） |
| **EV-S を使ってよい用途** | **禁止**（Completeness で PE 重み変更しない） | Completeness / EC / Contract Surface | read-only 入力（勝率再解釈禁止・ADR-010） |
| **EV-D を使ってよい用途** | **禁止**（ROI で Prediction 改変しない） | **禁止**（ROI を Core Completeness KPI にしない・ADR-009） | Ticket/Skip/Betting 研究 |

---

## 5. Product vs Core の対応表

| ユーザー用語 | Taxonomy | 備考 |
|---|---|---|
| Product Evidence | 主に **EV-P**（+ EV-D-FRI） | V8 RA パイプライン |
| Core Evidence | **EV-S** | ADR-009/010。現状は Research/Shadow 文書が主で、Product 永続ストアは未配線（V7/V8 Audit） |
| Decision Evidence | **EV-D**（FRI 除く Shadow 系） | ADR-008 配下 |

---

## Related

- Lifecycle: `v105-evidence-lifecycle.md`
- Ownership: `v105-evidence-ownership.md`
- Governance: `v105-governance.md`
