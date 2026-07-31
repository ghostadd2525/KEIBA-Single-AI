# Version 8.5 — Operations Mode（正式運用）

**Status:** OPERATIONS / LOCKED  
**Effective:** 2026-07-26  
**Baseline Lock:** **Version8.5**

Research Platform の実装フェーズは完了。以降は **運用・監視・品質保証** を優先し、新規 Research 機能の追加は停止する。

---

## 固定宣言

Version8.5 を正式 Operations Baseline とする。

- Research Platform の **新機能追加は停止**
- 実運用データに基づく改善サイクルのみ実行
- **PE / CE / AI / Production ロジック変更は禁止**
- 毎週改善案を作ることが目的ではない
- `decision = no_improvement` は **正常終了**（Version 維持 = 成功）

---

## 運用サイクル

### 土日 — Production

```
ResultAutomation → race_results → race_evaluations
→ Miss Evidence → Archive
```

| 実行 | 禁止 |
|------|------|
| ResultAutomation / race_results / race_evaluations / Miss Evidence / Archive | Analyzer / Proposal / Validation / Canary / Baseline / PE / CE / AI 変更 |

### 月〜金 — Research

```
Analyzer → Proposal → Validation → Canary → 285R Baseline
→ Decision → Knowledge → Governance → Weekly Report
```

| 曜日 | コマンド |
|------|----------|
| 月 | `npm run v8:mon` |
| 火 | `npm run v8:tue` |
| 水 | `npm run v8:wed` |
| 木 | `npm run v8:thu` |
| 金 | `npm run v8:fri` |
| 提出 | `npm run v8:report` |
| Incident（異常時） | `npm run v8:incident` |
| **日次自動化 (V8.6)** | `npm run v8:runner`（systemd 03:00 JST） |

詳細: [`v8.6-research-scheduler.md`](./v8.6-research-scheduler.md)

| 実行 | 禁止 |
|------|------|
| Analyzer〜Weekly Report | Production DB 更新 / Core Hot Patch / PE / CE / AI 変更 |

---

## Decision Rule

```
decision = no_improvement  → 正常終了（成功）
```

改善が無い週も Version8.5 維持として完了する。

---

## 毎週提出物

`development/weekly/{week}/reports/weekly-ops-report.md`（+ `.json`）

1. **Production Report** — ResultAutomation / race_results / race_evaluations / Miss件数 / Archive件数  
2. **Research Report** — Root Cause分布 / Proposal件数 / Validation Pass率 / Canary成功率 / Accept・Reject・no_improvement率  
3. **Knowledge Report** — Active / Stale / Archived / Merge Candidate / Average Knowledge Score  
4. **Analyzer Report** — Precision / Recall / Prediction Error / Confidence・Validation Calibration  
5. **KPI Report** — 285R 差分（Hit / Purchase / rank710 / other_miss / rank46）  
6. **Baseline Health Check**（必須）  
7. **Decision**  
8. PE / CE / AI 変更なし  

異常時のみ別途: **Incident Report**（`incident-report.{json,md}`）

---

## Baseline Health Check（毎週必須）

| 項目 | 内容 |
|------|------|
| PE変更 | 有無 |
| CE変更 | 有無 |
| AI変更 | 有無 |
| ResultAutomation正常 | OK / NG |
| Miss Evidence正常 | OK / NG |
| Knowledge更新 | OK / NG |
| Governance更新 | OK / NG |
| 285R比較実施 | OK / NG |
| Feature Flag誤ON | 有無 |
| Production Canary混入 | 有無 |
| Baseline Lock | Version8.5 |

---

## Incident Report（異常時のみ）

通常レポートとは別に提出。トリガ例:

**Production:** ResultAutomation失敗 / race_results取得失敗 / Miss Evidence未生成 / Archive失敗  

**Research:** Root Cause Precision 大幅低下 / Validation Score と実改善の継続乖離 / Knowledge Score 急落 / Canary で 285R 悪化  

**KPI:** Hit率急落 / rank710・other_miss・rank46 増加 / Purchase 成績悪化  

必須項目: 発生日時 / 影響範囲 / 原因候補 / 推奨対応 / Productionへの影響有無  

生成: `npm run v8:incident`（異常なしならファイル未作成・exit 0）

---

## 改善提案ルール

新しい Research 機能は **原則提案しない**。

提案は次をすべて満たす場合のみ:

1. 実運用で不足が確認された  
2. KPI 改善につながる Evidence がある  
3. 285R Baseline で改善可能性が確認できた  

提案時は必ず添付:

- 根拠 Evidence  
- KPI 比較  
- 285R Baseline 比較  
- 想定 ROI  

テンプレート: [`v8-improvement-proposal-template.md`](./v8-improvement-proposal-template.md)

---

## 完了条件（継続）

- Version8.5 を Operations Baseline として維持  
- 実運用データに基づく品質検証サイクルを継続  
- **機能追加より運用実績からの検証を優先**  
- 必要な改善だけを Evidence 付きで提案  
