# Version 3 — Production Rollout Plan

**Date:** 2026-07-24  
**Review ID:** `v3-production-readiness-review/1.0`  
**Parent:** [`v3-production-readiness-report.md`](./v3-production-readiness-report.md)  
**Decision:** **HOLD**（本 Plan は承認後の青写真 · **本 Round では配線しない**）

---

## 1. 目的

Lab Baseline v3 を本番に段階投入する場合の順序・ゲート・監視を定義する。  
**現時点ではいずれの Phase も実行しない。**

---

## 2. 対象スタック（配線時の意図）

| Stage | Mode | Flag（意図 ON） |
|-------|------|-----------------|
| Admission | A-03 | `F_V3_A03_POOL_ADMIT_ENABLED` |
| Selection | A-04 | `F_V3_A04_SEL_HISTORY_ENABLED` |
| Evaluation | A-01 | `F_V3_RANK_D1_ENABLED` |

| 明示 OFF | `F_V3_RANK_D2_ENABLED` · Representation ON · P3/P4 旧 Flag · Purchase V3 |
|----------|------|
| V2 | PE-V2-A との経路分離（二重適用禁止） |

---

## 3. ロールアウト段階

```text
V0  A-04 Validation（Lab）          ← 配線なし · HOLD 解除の前提
V1  実データ Offline Hard Gate      ← 配線なし
V2  Shadow（比較のみ）              ← 購入非実行 · 別承認
V3  Canary Flag ON（限定%）         ← 別承認
V4  全量                            ← 別承認
```

### V0 — A-04 Validation（必須 · 未実施）

| Gate | 条件 |
|------|------|
| 再現 | Hit 279 · churn vs Baseline v2 = 0 |
| 差分 | Boundary14 + Reorder10 · 悪化 0 |
| 隔離 | Evaluation/Admission モジュール非変更確認 |

### V1 — 実データ Offline（必須 · 未実施）

| Gate | 条件（案） |
|------|------------|
| Hard Gate | Hit > V2 Control（または合意した実データ Baseline）∧ churn=0 |
| 層 | Delete 以外の大規模退行なし |
| 禁止 | 本番 Flag ON |

### V2 — Shadow（別承認）

| 項目 | 内容 |
|------|------|
| 動作 | V3 pick をログ・比較のみ |
| 購入 | **実行しない** |
| Gate | V2 vs V3 pick 差分率 · 想定層の偏り · 例外率 |
| Rollback | Shadow 停止のみ（本番 pick 不変） |

### V3 — Canary（別承認）

| 項目 | 内容 |
|------|------|
| Flag | 3 Flag を限定トラフィックのみ ON |
| 監視 | Hit proxy · churn · ROI · p95 · エラー率 |
| Abort | [`v3-production-rollback-plan.md`](./v3-production-rollback-plan.md) L1 |
| 期間 | 合意した観察窓 |

### V4 — 全量（別承認）

| 項目 | 内容 |
|------|------|
| 前提 | V3 Canary Gate PASS · Explain/Ops 同期 |
| 監視 | 本番 KPI 継続 |
| Abort | L1 → L2 |

---

## 4. 監視メトリクス（配線後）

| メトリクス | 用途 |
|------------|------|
| Hit / Purchase | 精度 |
| churn vs 直前安定版 | 退行検知 |
| rank710 / rank46 / other | 層診断 |
| ROI | 補助 |
| p95 latency | SLA |
| Flag 実効状態 | 設定ドリフト |

---

## 5. 本 Round の実施範囲

| 実施 | Review 文書化のみ |
|------|-------------------|
| 非実施 | V0–V4 · Shadow · Canary · Flag ON · API 配線 |

---

## 6. 停止

Rollout Plan 定義完了。実行には別承認が必要。
