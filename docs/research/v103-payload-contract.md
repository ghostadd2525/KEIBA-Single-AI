# Version103 — Payload Contract（設計・未実装）

**Date:** 2026-07-28  
**Status:** Contract Surface 設計 · **実装禁止**  
**Parents:** V103 Export Matrix · ADR-009 · ADR-010 · V95/V96  
**Locks:** Prediction / World / Trigger / Near Miss **Logic** 非変更。追加は **serialize のみ**。

---

## 1. CoreRaceSemanticPayload（提案形）

消費: Single AI / Win5 AI（read-only）

```text
CoreRaceSemanticPayload
  schema: "core-semantic-payload/v103-design"
  race_id: string

  # --- already first-class (unchanged) ---
  prediction: { ranks[], scores[], top1 }   # Confidence確率なし
  world_id: CEW
  decision_trace: { world → {must, must_gaps, exclude, match} }
  transition: string | null
  trigger_path: string | null

  # --- PROMOTE_FIRST_CLASS (derived serialize only) ---
  near_miss: null | {
      residual_class: NEAR_MISS | PURE_RESIDUAL
      near_world: WorldId | null
      near_worlds: WorldId[]
    }
  affinity: null | {
      core_world: float
      midupper_world: float
      midhole_world: float
      rank7_world: float
      definition: "v96/must_affinity"
    }
  exclusion_reasons: {
      # per world that exclude==true, list of reason ids
      [world_id]: string[]
    }
  explanation_confidence: {
      semantic_confidence: float | null
      world_confidence: float | null
      near_miss_confidence: float | null
      trace_confidence: float | null
      explanation_confidence: float | null
      definition_version: "v101/1.0"
      not: ["prediction_probability", "odds", "calibration"]
    }

  # --- KEEP_DERIVED (reference only, not race-embedded strategy body) ---
  expected_strategy_ref: {
      registry: "v75-expected-strategy"
      key: world_id
      # body resolved by consumer from registry — optional embed of resolved id only
      strategy_id: string
    }

  # --- DO_NOT_EXPORT ---
  # natural_language_why:  ← 禁止
```

---

## 2. MUST / MUST NOT

| ID | 規則 |
|---|---|
| PCS-0 | Payload は既存 Trace からの **導出結果の公開**に限る |
| PCS-1 | Rank / Score / World Logic / Trigger を変更しない |
| PCS-2 | `explanation_confidence` を勝率・オッズ・Calibration と同一視しない |
| PCS-3 | `near_miss` を Positive World に昇格させない（CEW 不変） |
| PCS-4 | `affinity` は unsatisfied 以外では null |
| PCS-5 | Natural language why を Core payload に含めない |
| PCS-6 | Expected Strategy 本文のレース固有新造をしない（レジストリ参照） |
| PCS-7 | Decision Ticket/Skip を本 Payload に含めない |

---

## 3. 消費者契約

| Consumer | 読んでよい | してはならない |
|---|---|---|
| Single AI | 全 PROMOTE フィールド＋ prediction/world/trace | EC を勝率表示に使う / CEW 書き換え |
| Win5 AI | 同上（説明・監査） | Affinity/Near Miss で Positive Ticket 化（DL-C6） |
| Presentation | MS-6 相当文を **自層で生成** | Core に散文を要求 |

---

## 4. 実装ステータス

| 項目 | Status |
|---|---|
| 本 Contract 文書 | Done（V103） |
| 製品 serialize | **Not authorized** |
| Shadow emit runner | 別 Decision |

---

## 関連

- `v103-export-matrix.md`
- `v103-core-contract-surface.md`
- ADR-010 Explanation Confidence Bundle
