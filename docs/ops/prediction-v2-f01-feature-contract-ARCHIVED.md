# PV2-F01 Feature Contract — ARCHIVED

**Contract ID:** `expect-prediction-v2-market-features/1.0`  
**Status:** **ARCHIVED**（2026-07-21）  
**Decision:** Version 2 対象から **除外**。実装チケットは作成しない。

## 除外理由

| 項目 | 内容 |
|------|------|
| ROI Validation | [`prediction-v2-f01-roi-validation.md`](./prediction-v2-f01-roi-validation.md) |
| 実測 | odds 改善可能 **13 / 69 = 18.8%** |
| Go 条件 | **≥ 20%** 未達 |
| 構造限界 | Candidate Pool 外・大穴系ミスは市場微小補正（V2-A）で改善不能 |

## 後継

Version1 残ミス 69 件のテーマ別 ROI 再評価:  
[`prediction-v1-miss69-theme-roi-review.md`](./prediction-v1-miss69-theme-roi-review.md)

正本の詳細定義は履歴として本ファイルおよび `contracts/expect-prediction-v2-market-features/1.0/` に残すが、**実装の根拠には使わない**。
