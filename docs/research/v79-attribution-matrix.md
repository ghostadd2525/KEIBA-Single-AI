# Version79 — Attribution Matrix

**Date:** 2026-07-28  
**Parent:** `v79-pilot-attribution-design.md`  
**Status:** Design only — 実装禁止

---

## ④ Attribution Matrix（2×2）

行 = **WorldLabel (A)** / 列 = **PEPolicy (B)**

|  | **B = legacy_pe** | **B = pilot_pe** |
|---|---|---|
| **A = legacy** | **Cell LL**（Baseline） | **Cell LP**（通常は pilot 不発火※） |
| **A = cew** | **Cell CL**（Trigger-only） | **Cell CP**（Both / V78 相当） |

※ `pilot_pe` は発火条件で **CEW∧Ready** を要求するため、Cell LP は設計上 **legacy_pe と同一出力**（監査セル）。LP≠LL なら境界バグ。

---

## セル定義

| Cell | WorldLabel | PEPolicy | 役割 |
|---|---|---|---|
| **LL** | legacy | legacy_pe | Production 相当ベースライン |
| **CL** | cew | legacy_pe | ① Trigger のみ |
| **CP** | cew | pilot_pe | ③ Both（V78 Pilot 相当） |
| **LP** | legacy | pilot_pe | 境界監査（発火ゼロ期待） |

Strategy-only は **CL vs CP**（A=cew 固定）で読む。  
（表では横方向の移動。）

---

## 差分オペレータ

| 名前 | 計算 | 归因 |
|---|---|---|
| Δ_Trigger | CL − LL | Trigger / ラベルのみ |
| Δ_Strategy | CP − CL | Strategy / PE のみ |
| Δ_Both | CP − LL | 同時変更 |
| Interaction | CP − LL − (CL−LL) − (CP−CL) = 0（恒等） | — |
| Interaction（検算） | Δ_Both − Δ_Trigger − Δ_Strategy | 非加法の検出（定義上 0。実装バグ検出用に残す） |

層別:

| 層 | Δ_Strategy の主対象 |
|---|---|
| CEW=rank7 | rank7 Pilot |
| CEW=unsatisfied | Residual Pilot |
| CEW∉Ready | ≈0（必須） |

---

## 実験 → 結論 対応表（一意判定）

| 実験セット | 必須セル | 一意に言えること |
|---|---|---|
| Trigger 実験 | LL, CL | Δ_Trigger のみ報告可 |
| Strategy 実験 | CL, CP（Ready 層別） | Δ_Strategy のみ報告可 |
| Confounded（禁止を归因に使うな） | LL, CP のみ | **归因不可** — V78 パターン |
| 完全归因 | LL, CL, CP（+ LP 監査） | Trigger / Strategy / Both を分離報告可 |

---

## メトリクス（セルごと）

各 Cell で同一コーパス（285R）:

- Prediction Fingerprint  
- Hit / Purchase  
- rank710 / other_miss / rank46 等  
- pe_path 分布（legacy_pe / pilot_rank7 / pilot_unsat）  
- world_label_used 分布  

**禁止:** Hit 改善を归因成功の定義にすること。

---

## Ready World と行列の関係

| CEW | LL | CL | CP | LP |
|---|---|---|---|---|
| rank7 | Legacy PE | Legacy PE（文脈=CEW） | Pilot rank7 | 不発火期待 |
| unsatisfied | Legacy PE | Legacy PE（文脈=CEW） | Pilot residual | 不発火期待 |
| その他 | Legacy PE | Legacy PE | Legacy PE（発火なし） | 不発火期待 |

「文脈=CEW の Legacy PE」は、Legacy PE が World 入力を読む場合にのみ CL≠LL となりうる。読まない実装なら CL=LL（Δ_Trigger=0）が正しい归因結果。  
