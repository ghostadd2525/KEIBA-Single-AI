# Version96 — Residual Taxonomy Update

**Generated:** `2026-07-28T12:22:33+00:00`  
**Base:** V95 Residual Decision Taxonomy  
**Change type:** Metadata 精密化（CEW / World 非変更）

## 更新内容

V95 の `near_world`（priority primary）に加え、各 World の **連続 Affinity** を Meta に載せてよい（設計）。

```text
ResidualTaxonomyMeta (v96)
  world_id: "unsatisfied"
  residual_class: NEAR_MISS | PURE_RESIDUAL
  near_world: WorldId | null          # V95 primary（Exclusion）
  affinity: {
    core_world: float,                # must_affinity [0,1]
    midupper_world: float,
    midhole_world: float,
    rank7_world: float
  }
  affinity_top: WorldId
  affinity_confidence: HIGH|MED|LOW|VERY_LOW
  must_gaps_by_world: {...}
  exclusion_reasons_by_world: {...}   # Near Miss で必須保持
  taxonomy_version: "v96/1.0"
```

## V95 との差分

| 項目 | V95 | V96 |
|---|---|---|
| 分類 | NEAR_MISS / PURE_RESIDUAL | **同じ（維持）** |
| near_world | primary 1 ラベル | **維持** |
| Affinity vector | なし | **追加（観測）** |
| Must Gap / Exclusion | 構造定義のみ | **レース単位で保持** |
| CEW | unsatisfied | **変更なし** |

## 衝突ルール

1. `residual_class` は構造（Exclusion / Must全失敗）が優先。Affinity で上書きしない。
2. Decision の Explain/Risk 主キーは V95 どおり `near_world`（Near Miss）または `pure_residual`。
3. `affinity_top ≠ near_world` のときは **注記のみ**（Ticket 切替禁止）。
4. 実測: Near Miss で affinity-top≡primary 一致率 = 1.000。

## 禁止（維持）

- Affinity 高い → CEW 書き換え / 新 World 追加 / Positive Ticket 化
- unsatisfied 件数を減らすための Threshold 変更（本スタディの目的外）
