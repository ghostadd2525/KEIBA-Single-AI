# Version 3 — A-05 Shadow Rollout Plan

**Date:** 2026-07-24  
**Status:** Plan Only · **実行なし**  
**Parent:** [`v3-a05-shadow-design.md`](./v3-a05-shadow-design.md)  
**PRR:** HOLD（本 Plan 実行には別承認が必要）

---

## 1. 目的

A-05 Shadow を段階導入する順序と入場条件を定義する。  
**現時点ではいずれの段階も実行しない。**

---

## 2. 対象

| 項目 | 値 |
|------|-----|
| Stage | Admission A-05 のみ |
| Flag | `F_V3_A05_ADM_FAVSAFE_ENABLED` |
| 本番既定 | **OFF 維持** |
| 同時禁止 | A-03 ON |

---

## 3. 段階

```text
R0  設計承認（本ドキュメント）           ← 現在地
R1  Shadow 実装承認（別 Round）          ← 未着手
R2  S0 Dry-run（3–7日）
R3  S1 Shadow Hard Gate（≥14日 or N≥285）
R4  S2 安定観察（任意）
R5  Production 移行レビュー（別承認）
R6  Canary Flag ON（本番 Mesh · 別設計）
```

| 段階 | 本番購入 | 本番 Flag 既定 |
|------|----------|----------------|
| R0–R4 | Control のみ | OFF |
| R5 | レビューのみ | OFF |
| R6+ | 別 Rollout | 要承認 |

---

## 4. Rollout 条件（入場）

### R1 — Shadow 実装開始

| 条件 | 状態 |
|------|------|
| A-05 Accuracy PASS | Done |
| A-05 Validation PASS | Done |
| Shadow Design / Spec / Acceptance 承認 | 本 Round で文書化 · 人間承認待ち |
| PRR が Shadow 実装を許可 | **未**（HOLD） |

### R2 — Dry-run 開始

| 条件 |
|------|
| Shadow Runner が fail-open |
| 本番経路に差分なし（カナリア前スモーク） |
| メトリクスパイプラインが空回りで健全 |

### R3 — Hard Gate 窓開始

| 条件 |
|------|
| S0 で error_rate / mismatch が上限以下 |
| A1–A7 アラート接続 |

### R5 — Production 移行レビュー入場

| 条件 |
|------|
| Shadow Hard Gate PASS（Acceptance） |
| worsened_winner_rank1 = 0 を窓全体で維持 |
| ΔHit > 0 · churn_hit = 0 |
| 運用・Explain・API 影響レビュー完了（別文書） |

---

## 5. ロールアウト時の監視チェックリスト

- [ ] Hit / ΔHit 日次  
- [ ] worsened_winner_rank1 日次（ゼロ許容）  
- [ ] churn_hit / pick_churn  
- [ ] promote_rate / favsafe_block_rate  
- [ ] Shadow p95 / error_rate  
- [ ] Control 経路健全性（Shadow 非影響）  

---

## 6. 明示停止

本 Plan の文書化まで。R1 以降は実行しない。
