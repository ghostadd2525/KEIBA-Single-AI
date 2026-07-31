# Version 3 — Architecture Summary

**Date:** 2026-07-24  
**Status:** Final（V3 Close）  
**Parent:** [`v3-final-report.md`](./v3-final-report.md)

---

## 1. 論理パイプライン

```text
┌─────────────┐
│ Race Input  │  runners + context（結果列は入力禁止）
└──────┬──────┘
       ▼
┌─────────────┐
│Representation│  P2 Feature Generator（任意 · 既定 OFF）
└──────┬──────┘
       ▼
┌─────────────┐
│ Admission   │  A-05 Official Candidate
│             │  A-03 Deprecated · P3 Banded Deep（基盤）
└──────┬──────┘
       ▼
┌─────────────┐
│ Selection   │  A-04 History Crowding · P4 Reorder
└──────┬──────┘
       ▼
┌─────────────┐
│ Evaluation  │  A-01 D1 Primary · A-02 D2 Secondary
└──────┬──────┘
       ▼
┌─────────────┐
│ Purchase    │  Lab identity / 既存本番 Purchase
│             │  V3 専用 Purchase なし · Shadow 非購入
└─────────────┘
```

---

## 2. パッケージ境界

| 領域 | Path | ルール |
|------|------|--------|
| V3 Lab | `research/v3_lab/` | V2 Production を import しない |
| Shadow | `research/v3_lab/shadow/` | fail-open · 非購入 |
| Docs | `docs/releases/v3-*.md` | 正本 |
| V2 Production | （既存） | V3 Close 後も現行本番 |

---

## 3. 公式候補スタック（To-Be · 未配線）

| Stage | Component | Flag |
|-------|-----------|------|
| Admission | **A-05** | `F_V3_A05_ADM_FAVSAFE_ENABLED` |
| Selection | A-04 | `F_V3_A04_SEL_HISTORY_ENABLED` |
| Evaluation | A-01 | `F_V3_RANK_D1_ENABLED` |
| Purchase | 既存本番 | — |

| 除外 | A-03 · A-02 同時 ON · Lab Baseline v3 の本番適用 |
|------|------|

---

## 4. 評価二層（教訓）

| 層 | 役割 |
|----|------|
| Lab Accuracy（合成） | 層別介入の検証 |
| Offline / Shadow（実データ） | **本番外挿の Hard Gate** |

Lab のみ PASS で本番 GO しない（A-03 の教訓）。

---

## 5. 制御プレーン

| 機構 | 役割 |
|------|------|
| Feature Flags | すべて既定 OFF |
| A-03∧A-05 mutex | Hard reject |
| Shadow runtime env | 本番 Flag と分離 |
| PRR HOLD | 配線・ON の上位ゲート |

---

## 6. 参照

- Vision / Architecture Proposal: `v3-vision.md` · `v3-architecture-proposal.md`  
- Integration Design: `v3-production-integration-design.md`  
- Close: `v3-close-report.md`
