# Version105 — Evidence Ownership

**Date:** 2026-07-28  
**Status:** Design only · **実装禁止**  
**Parents:** V105 Taxonomy · Lifecycle · ADR-003/008/009/010 · V8 Ops · V103

---

## 一文

**Owner は「書ける人」であり、消費者は「読める人」である。跨クラスの書込は禁止。**

---

## 1. Owner 表（正規）

| Class | Owner（書込・スキーマ） | 共同閲覧（読取） | 根拠 |
|---|---|---|---|
| **EV-P** | **Ops / ResultAutomation**（生成）· **Research Analyzer Owner**（派生 Pattern） | Decision（Rank 読取）· Core（Completeness 監査時の Rank 有無確認のみ） | V8; ADR-003 |
| **EV-S** | **Core / World Semantic Owner**（trace・導出定義）· **Contract Owner**（PROMOTE 面） | Single AI / Win5（説明）· Decision（read-only・非勝率化） | ADR-009/010; V103 |
| **EV-D** | **Decision Owner** | Research Dashboard · Ops（フラグ） | ADR-008 |
| **EV-D-FRI** | **Research Friday Gate Owner**（提案採否） | Ops（週次レポート） | V8 Operations Baseline |

---

## 2. クラス別：Owner / 保存期間 / 更新条件 / 利用者 / 昇格条件

### EV-P Prediction Evidence

| 軸 | 定義 |
|---|---|
| **Owner** | ResultAutomation（Miss/Eval 生成）; Research（Analyzer→Knowledge） |
| **保存期間** | 週次 Hot → Archive Warm; Pattern は V8.5 Aging（8週） |
| **更新条件** | 結果確定後の評価/Miss 出力。PE ロジック変更での過去 Miss 改竄禁止 |
| **利用者** | Analyzer, Proposal, Canary, 285R Validation |
| **昇格条件** | Accept + Validation + Baseline 手続き。**EV-S へ昇格不可** |

### EV-S Semantic Evidence

| 軸 | 定義 |
|---|---|
| **Owner** | Core Completeness / World Contract Owner |
| **保存期間** | コーパス評価ウィンドウ + versioned research; 意味定義は版管理（捨てない） |
| **更新条件** | 再観測・導出再計算、または Contract 版上げ。Hit/ROI では更新しない |
| **利用者** | Completeness/EC 監査; 説明 UI; Decision read-only |
| **昇格条件** | V103 `PROMOTE_FIRST_CLASS` のみ。実装は別 Decision。**EV-P / ROI KPI へ昇格不可** |

### EV-D Decision Evidence

| 軸 | 定義 |
|---|---|
| **Owner** | Decision Owner（Ticket/Pool/Risk/Betting） |
| **保存期間** | Shadow 比較窓 + Verdict 永続（否定結果含む） |
| **更新条件** | Shadow 再実行・政策パラメータ変更。Trigger/PE/World Meaning 非更新 |
| **利用者** | Decision 研究・推奨パラメータ管理 |
| **昇格条件** | Shadow 合格後も Production ON は別 Gate。**Core Completeness 成功条件にしない** |

### EV-D-FRI（Product 金曜採否）

| 軸 | 定義 |
|---|---|
| **Owner** | Friday Research Gate |
| **保存期間** | Knowledge Base（V8.4/8.5） |
| **更新条件** | 週次 Accept/Reject/no_improvement |
| **利用者** | Research Metrics / Governance Pass |
| **昇格条件** | Accept された **EV-P 系提案**のみ。Semantic PROMOTE の代替にしない |

---

## 3. 書込権限マトリクス

| Actor | EV-P | EV-S | EV-D |
|---|---|---|---|
| ResultAutomation | Write | No | No |
| PE / Ranking | No（生成は Pred、Evidence 改竄 No） | No | No |
| Core / Trigger（ラベル生成は既存契約） | No | Write（trace/導出 Evidence） | No |
| Decision Layer | Read Rank only | Read（非勝率化） | Write |
| Analyzer / Friday Gate | Write derived / Accept | No | No（FRI ログのみ） |

---

## 4. 責任分界（RACI 要約）

| 関心事 | R | A | C | I |
|---|---|---|---|---|
| Miss 件数・Hit 改善 | Research Analyzer | Ops/RA | PE（提案時のみ） | Decision |
| World/NM/EC Completeness | Core Semantic | ADR-009 Owner | Decision（消費） | Ops |
| Ticket/Skip/Betting | Decision Owner | ADR-008 Owner | Core（入力提供） | Research |

R=実行 A=説明責任 C=協議 I=通知

---

## Related

- `v105-evidence-taxonomy.md`
- `v105-evidence-lifecycle.md`
- `v105-governance.md`
