# Explainability Phase 2 — Pool / Entry / RePick 実施レポート

**Date:** 2026-07-22  
**Status:** **実装完了 — 受領待ち**  
**設計:** `docs/releases/v2-explainability-design-review.md` §3.5 / §10 Phase 2  
**非対象:** Accuracy · UI Enhancement · Operations · Prediction API · RaceCardSummary 契約  
**Final Report:** **未作成**（指示どおり受領後まで停止）

---

## Feature Flag

| Flag | レイヤ | 既定 | 役割 |
|------|--------|------|------|
| `WIN5_EXPLAIN_V2_ENABLED` | Core | **false** | `explain_payload`（Phase 2 product_stages 含む） |
| `EXPLAIN_V2_ENABLED` | PI / BFF | **false** | pass-through / mapper |
| `v2_explain` | Web | **false** | 理由 UI（Pool/Entry/RePick 表示含む） |

Web 表示は **`v2_explain` 配下のみ**。全 Flag OFF ≡ v1.1。

---

## 実装要点

| 項目 | 内容 |
|------|------|
| Pool 理由 | PE journal → `stage=candidate_pool` + factor「Pool 理由」 |
| Entry 理由 | PE journal → `stage=entry` + factor「Entry 理由」 |
| RePick 理由 | RP journal → `stage=repick` + factor `kind=repick` |
| decision_trace | `product_stages` で stub（not_applied）を置換、`timestamp` / `reason_codes` 付与 |
| Explain Payload | `product_stages` 非 null · `pipeline_version=…-phase2` · `meta.explain_phase=2` |

Journal は Accuracy モジュールを import せず、dict 契約のみ消費（`_win5_pool_entry_v2_journal` / `_win5_repick_v2_journal` または `product_journals=`）。

---

## Flag OFF 恒等性

| 確認 | 結果 |
|------|------|
| Core Flag OFF → journals があっても `explain_payload=None` | PASS |
| BFF Flag OFF → product_stages があっても空 explain | PASS |
| Web `v2_explain: false`（beta.json） | PASS |
| Phase 1 E2E 回帰 11 PASS | PASS |

---

## 契約テスト結果

```text
# Core
python -m unittest discover -s services/win5-ai/platform/core-overlay/tests -p "test_explain*.py" -v
→ 6 passed

# BFF / Contract
node --test tests/contract/explain-v2.test.mjs
→ 9 passed

# Phase 1 E2E 回帰
node --test tests/contract/explain-v2-e2e.test.mjs
→ 11 passed
```

---

## Explain Payload サンプル

- Bundle 全体: `fixtures/explain/v2-explain-phase2-sample.json`
- Preview: `fixtures/explain/v2-explain-phase2-preview.html`
- PNG: `fixtures/explain/v2-explain-phase2-preview.png`

---

## 変更ファイル一覧

| ファイル | 内容 |
|----------|------|
| `services/.../core/explain/product.py` | **新規** journal → product_stages |
| `services/.../core/explain/__init__.py` | product_stages merge · pipeline phase2 |
| `functions/_lib/explainBuilder.js` | merge · Pool/Entry/RePick factors · explain_phase |
| `public/assets/api/prediction-bind.js` | trace に timestamp / reason_codes · product 強調 |
| `public/assets/screens.css` | `.explain-trace-product` 等 |
| `contracts/single-explain/1.0/labels.ja.json` | Pool/Entry/RePick ラベル |
| `services/.../tests/test_explain_product_phase2.py` | Core Phase 2 テスト |
| `tests/contract/explain-v2.test.mjs` | BFF Phase 2 契約テスト |
| `fixtures/explain/v2-explain-phase2-sample.json` | Explain Payload サンプル |
| `fixtures/explain/v2-explain-phase2-preview.*` | UI プレビュー / スクショ |
| `docs/releases/v2-explainability-design-review.md` | Phase 2 チェック · 受領待ち |
| `docs/ops/v2-explainability-phase2-report.md` | 本レポート |

---

**停止点:** Explainability Final Report は作成していません。受領をお待ちします。
