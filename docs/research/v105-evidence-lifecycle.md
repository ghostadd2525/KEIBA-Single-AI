# Version105 — Evidence Lifecycle

**Date:** 2026-07-28  
**Status:** Design only · **実装禁止**  
**Parents:** V105 Taxonomy · V8 Self-Improvement Cycle · V8.5 Research Governance · ADR-009/010 · V92

---

## 一文

**生成 → 索引 → 利用 → 老化 → Archive / Promote の段階は共通語彙とし、クラスごとに更新条件と昇格先を分ける。**

---

## 1. 共通状態機械（語彙のみ共有）

```text
COLLECTING → INDEXED → CONSUMABLE → AGING → ARCHIVED
                              ↓
                         PROMOTED（別ストア / Contract）
                              ↓
                         REJECTED / NO_PROMOTE
```

| 状態 | 意味 |
|---|---|
| COLLECTING | レース日・Shadow 実行中に生データ生成 |
| INDEXED | カタログ/DB 索引に載り参照可能 |
| CONSUMABLE | 当該 Owner の正規利用者が読取可 |
| AGING | 未再検証・未使用により減衰（KB は V8.5） |
| ARCHIVED | 本番改善経路から外し保存のみ |
| PROMOTED | 上位契約（Baseline / Contract Surface / Decision 既定）へ昇格 |
| REJECTED | 昇格審査否決。Evidence 自体は研究記録として残してよい |

**禁止:** EV-P の PROMOTED を EV-S Contract に流し込むこと。  
**禁止:** EV-S の PROMOTED を PE/Miss Analyzer の必須入力にすること。

---

## 2. クラス別ライフサイクル

### 2.1 Prediction Evidence（EV-P）

| 項目 | 定義 | 根拠 |
|---|---|---|
| **生成** | 土日 Production: RA → Miss / evaluations | `v8-self-improvement-cycle.md` |
| **索引** | `improvement_evidence_index` + `evidence/improvement/` | `result_automation.py` |
| **更新条件** | 結果確定後・`hit_at_1=0`（Miss）または評価行更新。予測ロジック変更では **遡及改竄禁止** | V8; ADR-003 |
| **保存期間** | **Hot:** 当該週 Research が消費するまで CONSUMABLE。**Warm:** Archive 後も path 参照可能。**Cold:** Knowledge Pattern 化したものは V8.5 Aging（未使用 ≥8週 → stale） | V8 Archive; `v8.5-research-governance.md` |
| **利用者** | Analyzer / Proposal / Canary / Research Metrics（読取）。Production PE は **直接更新しない** | V8 Non-goals |
| **昇格条件** | Friday Accept + Canary + 285R / Baseline 合格 → **Research Knowledge / 将来 Baseline**。**Semantic Contract への昇格は不可** | V8 Decision Rule; V8.2 Validation |
| **Snapshot 併存** | EV-P-SNAP は Miss と **混ぜない**（結果後 vs 予測時点） | `v92-evidence-platform.md` |

```text
EV-P: RA → Miss JSON → INDEX → Analyzer → Proposal → (Accept?) → Knowledge/Baseline
                                                         └→ Reject / no_improvement
```

---

### 2.2 Semantic Evidence（EV-S）

| 項目 | 定義 | 根拠 |
|---|---|---|
| **生成** | Core / Trigger 読取結果・Near Miss Taxonomy・Affinity 導出・EC Bundle・Completeness Shadow | ADR-009/010; V95–V101; V100 Shadow |
| **索引** | Research 報告・コーパス付帯（現状 Product 永続ストア未配線 — V7/V8 Audit）。将来ストアは **EV-P パスと分離必須** | `v7v8-evidence-layer-audit.md` |
| **更新条件** | （a）レース記述の再観測（意味契約固定のまま trace/導出を再計算）；（b）Contract 改訂時のみスキーマ更新。**Hit/Miss 件数では更新しない** | ADR-009; V75 C4/C5 |
| **保存期間** | **Hot:** 現行コーパス評価ウィンドウ（例: 285R 研究セット）。**Warm:** Versioned research docs。**Cold:** Contract 改訂後も旧 trace を再現可能に残す（意味の履歴）。数値 TTL の本番強制は未実装 → 本票は政策枠 | ADR-009 Completeness; V76 |
| **利用者** | Core Completeness 評価・Single/Win5 の **説明 UI（read-only）**・V103 公開面設計。Decision は読んでよいが勝率化禁止 | ADR-010 §4; V103 |
| **昇格条件** | V103 分類に従う: **PROMOTE_FIRST_CLASS** のみ Contract Surface 候補。KEEP_DERIVED / DO_NOT_EXPORT は race payload 昇格不可。実装配線は **別 Decision** | V103; `v103-governance.md` |
| **非昇格** | Natural Explanation（MS-6）; Expected Strategy の race 固有本文（MS-1） | V103 |

```text
EV-S: Observe(World/NM/Aff/EC) → Completeness/EC Audit → (PROMOTE_FIRST_CLASS?) → Contract Surface候補
                                      └→ research archive only
      ※ Miss Analyzer / PE Canary 経路へは接続しない
```

---

### 2.3 Decision Evidence（EV-D）

| 項目 | 定義 | 根拠 |
|---|---|---|
| **生成** | Decision Shadow / Betting trial / ROI attribution / Affinity value test | V89–V98; ADR-008 |
| **索引** | Research docs + shadow runner 出力（Production 既定 OFF） | ADR-008 Feature Flags |
| **更新条件** | Shadow 再実行・政策パラメータ変更時。**World Meaning / Trigger / PE Rank は更新しない** | ADR-008 DL 契約; ADR-009 MUST NOT |
| **保存期間** | **Hot:** 当該 Shadow 比較ウィンドウ。**Warm:** Verdict 文書（例: V97 NO_VALUE）。**Cold:** 政策採用後も否定結果を保持（再仮説防止） | V97/V98 記録方針 |
| **利用者** | Decision Owner（Ticket/Skip/Betting）。Core Completeness KPI **禁止** | ADR-009 §3 |
| **昇格条件** | Shadow 合格 + ADR-008 Production 未承認のままでは **Research 推奨パラメータ**まで。Production ON は **別 Decision Gate** | ADR-008 Status |
| **EV-D-FRI** | 週次 Accept/Reject は **EV-P 改善ゲート**。保存は Knowledge Base。Semantic 昇格条件に使わない | V8.4 / V8.5 |

```text
EV-D: Shadow/Trial → Metrics(ROI/Coverage/…) → Verdict → (Recommend Betting/Skip?) → 別Gateで Production
                     └→ NO_VALUE / Residual 記録を永続（再混同防止）
```

---

## 3. 昇格マトリクス（要約）

| Class | 昇格先（許可） | 昇格先（禁止） |
|---|---|---|
| EV-P | Knowledge Pattern / PE 改善提案（Research） / Baseline 候補 | World Meaning · EC Contract · Ticket 既定 |
| EV-S | Contract Surface（PROMOTE 集合のみ） / Completeness 指標定義 | PE 重み · Miss RootCause 必須入力 · ROI KPI |
| EV-D | Decision 推奨パラメータ（Shadow） | Core Completeness 成功定義 · CEW ラベル改変 |

---

## 4. 老化（Aging）の適用範囲

| 対象 | Aging 規則 | 根拠 |
|---|---|---|
| Research Knowledge Patterns（主に EV-P 由来の PAT） | active → stale（≥8週未使用）→ archived | V8.5 |
| EV-S Contract 定義 | **Aging で意味を捨てない**。改訂は ADR/Contract 版上げ | ADR-009 Semantic 固定思想 / V75 |
| EV-D 否定結果（NO_VALUE） | stale 化してよいが **削除して再発明禁止** | V97 記録 |

---

## Related

- `v105-evidence-taxonomy.md`
- `v105-evidence-ownership.md`
- `v105-governance.md`
