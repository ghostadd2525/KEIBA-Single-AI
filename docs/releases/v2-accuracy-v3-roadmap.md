# Version 3 Accuracy — Roadmap Update（V2 検証終了後）

**Date:** 2026-07-22  
**Status:** Roadmap Update（設計のみ・実装禁止） — **上位正本は V3 Design 一式**  
**前提:** Version 2 Accuracy **検証終了** — Final Report 受領  
**V2 Final 構成:** Phase255 + **PE-V2-A のみ**（Hit **218**）  
**正本（V2）:** `docs/releases/v2-accuracy-final-report.md`  
**正本（V3 設計）:** [`v3-design-report.md`](./v3-design-report.md) · [`v3-experiment-roadmap.md`](./v3-experiment-roadmap.md) · [`v3-accuracy-strategy.md`](./v3-accuracy-strategy.md) · [`v3-architecture-proposal.md`](./v3-architecture-proposal.md) · [`v3-vision.md`](./v3-vision.md)

> 本ファイルは V2 終了直後の短い引き継ぎメモ。Version 3 の正式設計は上記 V3 Design 文書を用いる。

---

## 0. V2 からの引き継ぎ

| V2 結論 | V3 への意味 |
|---------|-------------|
| PE-V2-A **採用** | V3 Control の既定スタックに含める（Hit 218 ロック） |
| RP-V2-A **不採用** | NEAR 系 RP を再挑戦しない。新 Trigger は別名・別設計 |
| CE-V2-A **不採用** | 温度較正の単純継ぎ足しは禁止。Evaluation は再設計 |
| CE-V2-C / RO-V2 未実施 | V2 終了により **V3 候補**へ移動（必須ではない） |
| 28 Feature 固定 | **新 Feature なしでは改善限界**を前提にする |

### V2.2 Roadmap の更新（クローズ）

| Phase（旧 V2.2） | 更新 |
|------------------|------|
| Phase A 設計 | **完了** |
| Phase B CE-V2 | CE-V2-A **FAIL** でクローズ。Facet C **実施しない** |
| Phase C PE-B/C | V2 検証終了のため **持ち越し（任意）** |
| Phase D RO-V2 | **V3 候補** |

旧文書 `docs/releases/v2-accuracy-v2.2-roadmap.md` は履歴参照用。以降の計画は **本 V3 Roadmap** を正とする。

---

## 1. Version 3 の目標（案）

```text
Control  = V2 Final（PE-V2-A ON）Hit = 218
Goal     = Hit > 218（かつ churn_hit = 0）
制約     = Delete 変更禁止 / 勝者リーク禁止 / 単独 Flag AB
```

V3 は「V2 Flag の延長」ではなく、**残 miss の構造に対する新しいレバー**を設計するフェーズとする。

---

## 2. 持ち越し課題（優先）

### P0 — 限界認識

**新 Feature を使わない範囲では改善限界。**  
V2 で Pool 入場（PE）以外のレバー（RP-NEAR / CE 温度）は Hit を上げられなかった。

### P1 — Evaluation不足

| 項目 | 内容 |
|------|------|
| 対象 | G1 遠位（surv≫N+2）等 |
| V2 | CE-V2-A FAIL |
| V3 案 | 表現・学習・（契約済みの場合のみ）新 Feature。単純温度再 AB は非推奨 |

### P2 — 境界不足 + 新 Trigger

| 項目 | 内容 |
|------|------|
| 対象 | surv≈N+2 の境界 4 / surv≤N なのに枠外の並べ替え 4 |
| V2 | RP Rescue 0/11 |
| V3 案 | **新 Selection / Reorder Trigger**（旧 RP-V2-A とは別 ID）。匿名・N 不変 |

### P3 — 新 Feature（条件付き）

| 項目 | 内容 |
|------|------|
| 前提 | 別 Feature Contract + ROI Validation（F01 は再開しない） |
| 位置 | Evaluation / 境界の天井を超えるための候補。必須パスではない |

### 対象外（継続）

- Delete Boundary  
- G1 allowlist 本番トリガ  
- RP-V2-A / CE-V2-A のパラメータ再挑戦  

---

## 3. 推奨シーケンス（設計のみ）

```text
V3-0  Control ロック文書化（PE-V2-A = Hit 218）
V3-1  残 miss 再分類（V2 Final 基準・285R）
V3-2  新 Trigger 設計レビュー（Reorder / Selection）← 実装は別承認
V3-3  Evaluation 再設計（学習 or 契約 Feature）← ROI ゲート
V3-4  単独 AB（Hard Gate: Hit>218 ∧ churn=0）
```

**禁止（当面）:** RP-V2 / CE-V2-A の再実装、複数 Flag 同時 ON、Delete 変更。

---

## 4. Flag 状態（V2 Final → V3 開始時）

| Flag | V2 Final | V3 開始時 |
|------|----------|-----------|
| `WIN5_POOL_ENTRY_V2_ENABLED` | **ON（採用）** | ON 維持（Control） |
| `WIN5_REPICK_V2_ENABLED` | OFF | OFF |
| `WIN5_CE_V2_ENABLED` | OFF | OFF |

---

## 5. 参照

| 文書 | パス |
|------|------|
| V2 Final Report | `docs/releases/v2-accuracy-final-report.md` |
| Experiment Summary | `compare/v2_accuracy_experiment_summary.csv` |
| G1 層分類 | `compare/v2_accuracy_g1_layer_classification.csv` |
| 旧 V2.2 Roadmap（履歴） | `docs/releases/v2-accuracy-v2.2-roadmap.md` |
