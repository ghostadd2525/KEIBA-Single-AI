# Version 2 Explainability — Final Report

**Date:** 2026-07-22  
**Status:** **実装完了（Phase 1–3）**  
**設計正本:** `docs/releases/v2-explainability-design-review.md`  
**判定:** Phase 1 RC · Phase 2 PASS · Phase 3 本レポートで提出

| 提出物 | パス |
|--------|------|
| 本 Final Report | `docs/releases/v2-explainability-final-report.md` |
| 設計レビュー | `docs/releases/v2-explainability-design-review.md` |
| Phase 1 E2E | `docs/ops/v2-explainability-phase1-e2e-report.md` |
| Phase 2 | `docs/ops/v2-explainability-phase2-report.md` |
| Phase 3 | `docs/ops/v2-explainability-phase3-report.md` |

---

## 0. エグゼクティブサマリー

Version 2 Explainability は、Prediction 画面の「なぜ ◎ か」を **explain 2.1（additive）** で構造化し、Product journal（Pool/Entry/RePick）と Kaoba `explain_pick` まで接続した。

| 結果 | 内容 |
|------|------|
| **契約** | Bundle 2.0 維持 · `explain.schema_version: single-explain/2.1` |
| **決定打** | `reason.decision_key` |
| **信頼度** | `confidence_reason` + contribution/weight |
| **トレース** | `decision_trace.stages[]`（CE → Product → mark） |
| **会話** | Kaoba / Conversation が reason を注入（`v2_explain`） |
| **Flag OFF** | **v1.1 恒等**（空 explain / 旧 Kaoba） |

---

## 1. Phase 一覧

| Phase | スコープ | STATUS |
|------:|----------|--------|
| 1 | CE + World + Confidence + mark · Core→PI→BFF→Web | **PASS（RC）** |
| 2 | Product journal → Pool / Entry / RePick | **PASS** |
| 3 | Kaoba `explain_pick` · Payload/UI/trace 最終統合 | **提出** |

---

## 2. Feature Flag（横断）

| Flag | レイヤ | 既定 |
|------|--------|------|
| `WIN5_EXPLAIN_V2_ENABLED` | AI Core | **false** |
| `EXPLAIN_V2_ENABLED` | PI / BFF | **false** |
| `v2_explain` | Web（+ Kaoba context） | **false** |

**原則:** 全 OFF ≡ v1.1（explain 空 · Kaoba 旧ルール）。

---

## 3. Flag OFF 恒等性（横断）

| 領域 | 結果 |
|------|------|
| Core OFF → `explain_payload` 省略 | PASS |
| BFF OFF → 空 `reasons`/`narrative` | PASS |
| Web OFF → v2 UI / KAOBA CTA なし | PASS |
| Kaoba: `v2_explain` なし → explain_pick 注入なし | PASS |
| Phase 1 E2E Flag 行列 | PASS（11） |

---

## 4. テスト結果（横断）

```text
Core test_explain*.py                         → 6 PASS
explain-v2.test.mjs                           → 9 PASS
explain-v2-phase3-kaoba.test.mjs + kaoba      → 含めて 25 PASS（合同実行）
explain-v2-e2e.test.mjs                       → 11 PASS
```

---

## 5. Explain Payload サンプル

| Phase | パス |
|------:|------|
| 設計例 | 設計書 §7 |
| Phase 2 | `fixtures/explain/v2-explain-phase2-sample.json` |
| **Phase 3 最終** | `fixtures/explain/v2-explain-phase3-sample.json` |

最終サンプルは `explain` 2.1 + `decision_trace`（Pool/Entry/RePick）+ `kaoba_explain_pick` 投影を含む。

---

## 6. スクリーンショット

| Phase | PNG |
|------:|-----|
| 1 | `fixtures/explain/v2-explain-ui-preview.html`（既存） |
| 2 | `fixtures/explain/v2-explain-phase2-preview.png` |
| 3 | `fixtures/explain/v2-explain-phase3-preview.png` |

---

## 7. アーキテクチャ（最終）

```text
AI Core explain_payload (+ product_stages)
  → PI pass-through
  → BFF explainBuilder → PredictionBundle.explain 2.1
  → Web race.html（v2_explain）
  → Kaoba / Conversation explain_pick（context.v2_explain）
```

---

## 8. 非対象（意図的に未変更）

- Accuracy / WIN5 PE·RP·CE ロジック本体
- UI Enhancement（RaceCardSummary / 一覧）
- Operations
- Prediction API 契約（additive `explain_payload` のみ）
- RaceCardSummary 契約

---

## 9. 運用メモ

1. 本番は Core/PI/BFF の Explain Flag と Web `v2_explain` を段階 ON。
2. Product 理由は journal が meta に載る経路でのみ `applied`（PI CE のみなら `not_applied` 維持）。
3. Kaoba は `chat.html` が `context.v2_explain` を付与したときだけ構造化理由を返す。

---

## 10. 完了判定

| 項目 | 判定 |
|------|------|
| Phase 1–3 実装 | **完了** |
| Flag 既定 false | **OK** |
| Flag OFF 恒等 | **OK** |
| 契約・E2E テスト | **OK** |
| Final Report | **本文書** |

**Explainability Version 2 — 実装クローズ（受領待ち）。**
