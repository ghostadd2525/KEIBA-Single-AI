# Version108 — Compatibility Matrix

**Date:** 2026-07-28  
**Mode:** Shadow Validation · 実装禁止  
**Parents:** ADR-011 · V107 · V106 · V105 · Core Platform Version1

---

## 凡例

| 記号 | 意味 |
|---|---|
| ✅ | 互換・破壊なし（契約上） |
| ⚠ | 条件付き（Registry/Flag/版一致が必要） |
| ❌ | 非互換または禁止結合 |
| — | 非接続（意図的） |

---

## Matrix A — Core Version1 × Consumer

| Core 要素 (v1) | Single Consumer | Win5 Consumer | 契約破壊経路 |
|---|---|---|---|
| prediction ranks/scores | ✅ 読取 | ✅ 読取 | mutate → ❌ ADR-003 |
| world_id | ✅ Registry キー | ✅ Registry キー | CEW 書換 → ❌ |
| near_miss / class | ✅ ⚠ unsatisfied | ✅ ⚠ unsatisfied | Positive Ticket 化 → ❌ DL-C6 |
| affinity | ✅ 説明のみ | ✅ 説明のみ | 自動 Skip → ❌ V97 |
| exclusion_reasons | ✅ Presentation | ✅ 監査 | — |
| explanation_confidence | ✅ 警告表示 | ⚠ 選定補助のみ | 勝率化/単独閾値 → ❌ |
| transition / must_gaps | ✅ | ✅ | — |
| expected_strategy_ref | ⚠ Registry 必須 | ⚠ 任意 | 本文を Core に埋込 → ❌ |
| Ticket in Core | — | — | 存在させない ✅ PCS-7 |

---

## Matrix B — API 層互換

| From ↓ / To → | Core API v1 | Consumer Single v1 | Consumer Win5 v1 |
|---|---|---|---|
| Core API v1 | ✅ | ✅ 入力 | ✅ 入力 |
| Consumer Single v1 | ❌ 逆流禁止 | ✅ | —（別 Product） |
| Consumer Win5 v1 | ❌ 逆流禁止 | — | ✅ |
| Decision Registry | —（参照のみ） | ✅ | ✅ |
| EXT Market/Card | — | ✅ | ✅ |

---

## Matrix C — Evidence Version 互換（V105）

| Evidence | Core v1 | Consumer Product | 昇格先 |
|---|---|---|---|
| EV-P | —（入力正本にしない） | Analyzer のみ | Knowledge（Semantic 不可） |
| EV-S | ✅ Completeness 観測 | 説明監査 | Contract Surface のみ |
| EV-D | — | Ticket/Coverage 結果 | Decision 推奨（Core KPI 不可） |

混在ストア: ❌

---

## Matrix D — Flag / Legacy

| 状態 | Core 契約 | Consumer 契約 | Prediction |
|---|---|---|---|
| 全 Consumer Flag OFF | ✅ 不変 | Legacy 経路 | ✅ 不変 |
| CORE_V103 OFF | 最小 payload | PROMOTE 欠落を許容（説明劣化） | ✅ |
| CORE_V103 ON / Consumer OFF | ✅ Shadow 可 | Product 非露出可 | ✅ |
| 意味変更デプロイ | ❌ Version1 違反 | ❌ | ❌ |

---

## Matrix E — 将来拡張との互換（予告）

| 拡張 | Core v1 互換条件 |
|---|---|
| 新 world_id 値 | 列挙拡張は **minor または Registry のみ**。既存値の意味変更 ❌ |
| 新 PROMOTE フィールド | Core **minor** + Consumer 無視可能（前方互換） |
| フィールド削除 | Core **major** のみ |
| 新 Decision 出力 | Consumer minor。Core 非変更 ✅ |

---

## 要約

| 組み合わせ | 結果 |
|---|---|
| Core v1 ↔ Single v1 | ✅ 互換（Registry/EXT 前提） |
| Core v1 ↔ Win5 v1 | ✅ 互換（同上） |
| Consumer → Core 書込 | ❌ |
| Evidence 横断 KPI | ❌ |

---

## Related

- `v108-platform-readiness-report.md`
- `v108-versioning-policy.md`
