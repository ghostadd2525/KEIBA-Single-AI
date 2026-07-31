# Version79 — Shadow Configuration（Attribution）

**Date:** 2026-07-28  
**Parent:** `v79-pilot-attribution-design.md` / `v79-attribution-matrix.md`  
**Status:** Design only — **実装禁止** / Production 非変更

---

## ⑤ Shadow 構成の目的

Production を動かさず、同一入力レースに対して **Attribution Matrix の全セル**を並列観測する。

```text
Production:  Trigger=Legacy, PE=Legacy     ← 変更禁止
Shadow:      Cells {LL, CL, CP, LP} を評価ログ
```

---

## Shadow 出力（レース単位）

| フィールド | 内容 |
|---|---|
| `race_id` | キー |
| `legacy_world` | Production Trigger 出力（現行） |
| `cew_world` | CEW / V69（V73 と整合） |
| `cell_LL_*` | Baseline 予測要約（fingerprint 部品） |
| `cell_CL_*` | CEW + legacy_pe |
| `cell_CP_*` | CEW + pilot_pe（Ready 時） |
| `cell_LP_*` | legacy + pilot_pe（監査） |
| `pe_path_CP` | legacy_pe / pilot_rank7 / pilot_unsat |
| `flags_snapshot` | 下記 Shadow Flag |

Prediction 全体を 4 本持つ場合は fingerprint をセル別に記録。

---

## Shadow Flag（Production Flag と分離）

V78 の `W_PE_PILOT_*` は将来の本番 Pilot 用。  
Attribution Shadow は **別名前空間**（設計）:

```text
W_ATTR_SHADOW_ENABLE     # OFF=Shadow 非実行（既定 OFF）
W_ATTR_RUN_LL            # 既定 ON（Shadow 有効時）
W_ATTR_RUN_CL
W_ATTR_RUN_CP
W_ATTR_RUN_LP            # 監査
```

| 規則 | |
|---|---|
| Production PE / Trigger | Shadow Flag を読まない |
| `W_ATTR_*` ON | ログと研究評価のみ |
| 既定 | すべて OFF または Shadow 無効 |

V78 Pilot Flag を Attribution と共用しない（関心混線防止）。

---

## 推奨 Shadow 実験バッチ（研究）

| Batch | 有効セル | 目的 |
|---|---|---|
| ATTR-T | LL, CL | ① Δ_Trigger |
| ATTR-S | CL, CP | ② Δ_Strategy（Ready 層別） |
| ATTR-B | LL, CP | ③ Δ_Both（参考・归因単独禁止） |
| ATTR-FULL | LL, CL, CP, LP | 完全归因 + 境界監査 |

285R で Batch を回し、行列差分を報告する（実行は別 Decision）。

---

## 境界監査（LP / Non-Ready）

| チェック | PASS 条件 |
|---|---|
| LP ≡ LL | pe_path 常に legacy_pe、予測一致 |
| CP on Non-Ready | pe_path = legacy_pe |
| CP on rank7 + flag | pe_path = pilot_rank7 |
| CP on unsat + flag | pe_path = pilot_unsat |

FAIL 時は Attribution 無効（実装バグまたは契約違反）。

---

## Production との関係

| 項目 | Shadow | Production |
|---|---|---|
| Trigger | Legacy を記録 + CEW 併記 | Legacy のみ採用 |
| PE | 4 セル評価 | Legacy のみ（本設計フェーズ） |
| Flag | `W_ATTR_*` | 未導入 / OFF |

Attribution が終わるまで **V78 Production Pilot ON は推奨しない**（归因不能な Δ_Both のみが残るため）。

---

## ログ保持

- セル別 Prediction Fingerprint  
- 層別 Hit / rank710 / other_miss  
- Δ_Trigger / Δ_Strategy / Δ_Both 表  

推測で欠損セルを埋めない。  
