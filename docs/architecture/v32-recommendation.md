# Version32 — Recommendation (Design Only)

**Date:** 2026-07-27  
**ADR:** `v32-world-adr.md`  
**Question:** どの案が設計思想「World は AI 最上流の勝ち筋分類」に最も適合するか

---

## ⑤ Recommendation

### Primary recommendation

# **P4 — Signal Service 分離 / World Input Contract 共通化**

### Binding intent (not an implementation order)

- Production / Research は **同一の World Input Contract** を正本とする。  
- 日次特徴の列数（116 vs 72/74）は **従属詳細**であり、World 正本ではない。  
- 契約を満たす供給手段として、現行運用を壊しにくいのは **P2（PI daily への正式 pace Signal 移植）**。  
- 運用が legacy パイプラインを再所有できるなら **P1** も契約充足手段として許容。

### Explicit rejects

| Option | Decision |
|--------|----------|
| **P3** | **Reject** — Research と Production で最上流 World 入力が分岐し、思想に反する |
| **P5 threshold-only** | **Reject** — 欠落信号を閾値で隠蔽する |
| **DEFAULT 0.5 を正式 World 仕様として追認** | **Reject** — フォールバックの恒常化であり、勝ち筋分類ではない |

---

## Why P4 best matches the design philosophy

1. **最上流の定義が列スキーマではなく分類入力になる**  
   World の仕事は「116列 CSV を読むこと」ではなく、「勝ち筋を条件信号で分類すること」。  
   V31 が示した契約分裂（116 design vs 72 ops）は、正本を **列数**に置く限り再発する。

2. **Production と Research の単一真理**  
   V25–V29 は Research が Production meta を写すことを示した。  
   最上流分類を統治するには、観測系と本番系が **同じ入力契約**を共有する必要がある（P3 否定）。

3. **断絶の本質に indirection を置く**  
   真の断絶は daily writer 置換（V31）。  
   P4 は「誰が CSV を書くか」と「World が何を必要とするか」を分離し、P1/P2 を実装手段として選択可能にする。

4. **拡張（chaos 等）を同型で扱える**  
   difficulty 以外の断絶（V26 chaos）も、同一 World Input Contract の欠番として管理できる。

---

## Why not P1 alone as the ADR headline

P1 は Original Architecture への忠実度は最高だが、思想の核は「116列そのもの」ではない。  
P1 を唯一の正本にすると、再び **搬送形態**が契約になってしまう。  
P1 は **P4 契約を満たす実装オプション**として残す。

---

## Why not P2 alone as the ADR headline

P2 は実務上もっとも自然な供給路だが、見出しを「72列へ移植」にすると、また列数契約に戻る。  
設計判断としては **「必要な pace/World Signals を Production 正本経路で正式生成する」** が本質であり、それは P4 の下での P2 バインディングと述べるべきである。

不完全な P2（style_entropy / pace_collapse 欠落のまま difficulty だけ等）は **設計不適合**（偽設計値）。

---

## Design contract to freeze (intent text)

以下を **正式な設計契約（未実装）** として記録する:

```text
World Input Contract (design-canonical)
--------------------------------------
World Trigger / WorldClassifier は、次を「欠落時 DEFAULT 恒常化」ではなく
設計信号として受け取ることを前提とする:

  - race_leg_difficulty     (designed formula; not STABLE default-as-policy)
  - chaos_score             (must be explicitly present or explicitly deferred
                             by a separate decision — currently broken/orthogonal)
  - short_field_pressure, phase_transition, late_stop, sustained, high_pace
    (existing Trigger reads; quality depends on upstream)

Pace signal prerequisites for designed difficulty include at least:
  win5_leg, horse_count (or contracted alias), pace_collapse_risk
  (or contracted bridge from *_v2), style_entropy, style counts as in formula.

Feature CSV width (116 vs 72/74) is a delivery detail.
Production and Research MUST share this World Input Contract.
DEFAULT 0.5 remains a missing-column safety fallback, NOT a World policy.
```

---

## Out of scope (this phase)

- コード変更、CSV 変更、Feature 追加実装  
- World / Trigger / Prediction / Production 変更  
- どの Sprint で P2 vs P1 を実装するかの工程確定  
- chaos_score 修復の方式決定（別判断）

---

## Decision record

| Field | Value |
|-------|-------|
| Recommended architecture | **P4** |
| Preferred production binding | **P2**（契約完全充足時） |
| Acceptable alternate binding | **P1** |
| Rejected | **P3**, threshold-only P5, DEFAULT-as-World-policy |
| Implementation approved? | **No** |
| Next gate | Explicit implementation ADR / change request（別承認） |

---

## Guardrails

- 設計推奨のみ。改善実装禁止を遵守。
