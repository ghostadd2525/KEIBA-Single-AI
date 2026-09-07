# Version 3 — A-05 Shadow Acceptance Criteria

**Date:** 2026-07-24  
**Status:** Criteria Locked for future Shadow Round · **検証実行なし**  
**Parent:** [`v3-a05-shadow-design.md`](./v3-a05-shadow-design.md)  
**Candidate:** A-05 · Flag `F_V3_A05_ADM_FAVSAFE_ENABLED`

---

## 1. 成功の定義（一文）

> Shadow 窓において、本番 Control を壊さず、A-05 が  
> **worsened_winner_rank1 = 0** かつ **ΔHit > 0** かつ **churn_hit = 0** を満たす。

---

## 2. Shadow Hard Gate（Must Pass）

| ID | Criteria | 閾値 |
|----|----------|------|
| H1 | `worsened_winner_rank1` | **= 0** |
| H2 | `ΔHit`（Shadow − Control） | **> 0** |
| H3 | `churn_hit`（Control Hit→Shadow Miss） | **= 0** |
| H4 | 評価窓 | ≥14 日 **または** ラベル済み N≥285 |
| H5 | 入力一致 / リークなし | PASS |
| H6 | A-03 同時 ON | なし |
| H7 | 本番 Flag 既定 | A-05 **OFF** 維持 |
| H8 | 本番 Control 健全性 | Shadow 開始前後で合意悪化なし |
| H9 | Shadow 障害 | error_rate / p95 ≤ 合意上限 |

**H1 欠落は即 FAIL（窓不合格）。**

---

## 3. Should Pass（Strong Soft）

| ID | Criteria |
|----|----------|
| S1 | `improved ≥ 1`（ΔHit の内訳が空でない） |
| S2 | `promote_rate` が Offline 校正帯から極端に乖離しない |
| S3 | 仮想 ROI が Control 以上（必須ではないが望ましい） |
| S4 | favsafe_block が短オッズ本命帯で機能している形跡 |

---

## 4. Production 移行条件（Shadow PASS 後 · 別承認）

Shadow Hard Gate PASS は **必要だが十分ではない**。

| ID | 条件 |
|----|------|
| P1 | Shadow H1–H9 PASS |
| P2 | PRR が HOLD → 条件付き GO（または Shadow 専用承認） |
| P3 | Canary Rollout / Rollback 手順の運用承認 |
| P4 | Prediction / UI / Ops / Explain 影響レビュー完了 |
| P5 | A-03 置換方針（Baseline v3 との関係）が文書決定 |
| P6 | 本番 Flag 既定は Canary までは **OFF** |

P1–P6 すべて満たすまで **Production 配線しない**。

---

## 5. Fail（Shadow 不合格）

| 条件 | 扱い |
|------|------|
| worsened_winner_rank1 > 0 | FAIL · L0 停止 |
| ΔHit ≤ 0（窓終了時） | FAIL |
| churn_hit > 0 | FAIL |
| 本番経路汚染 | FAIL · L2+ |
| Flag 既定が ON に変更された | プロセス FAIL |

---

## 6. Offline との対応

| Offline Validation | Shadow |
|--------------------|--------|
| Control 59 / A-05 66 | 実開催で同方向を期待（数値一致は不要） |
| wr1=0 · churn=0 · ΔHit>0 | **同一 Hard 思想** |
| improved 7 race_id | 再現必須ではない（分布差） |

---

## 7. 本 Round

Acceptance Criteria を固定したのみ。  
Shadow 実装・測定・Production 移行は行わない。PRR は HOLD。
