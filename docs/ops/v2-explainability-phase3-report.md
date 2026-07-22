# Explainability Phase 3 — Kaoba explain_pick 実施レポート

**Date:** 2026-07-22  
**Status:** **実装完了**  
**設計:** `docs/releases/v2-explainability-design-review.md` §10 Phase 3  
**非対象:** Accuracy · UI Enhancement · Operations · Prediction API · RaceCardSummary 契約

---

## Feature Flag

| Flag | 既定 | 役割 |
|------|------|------|
| `v2_explain` | **false** | Web UI + Kaoba `context.v2_explain` 注入ゲート |
| `EXPLAIN_V2_ENABLED` / `WIN5_EXPLAIN_V2_ENABLED` | false | explain 2.1 生成（既存） |

Kaoba への reason 注入は **`context.v2_explain === true`** のときのみ。Flag OFF ≡ v1.1 Kaoba 応答。

---

## 実装要点

| 項目 | 内容 |
|------|------|
| Kaoba explain_pick | `explainPick.js` → `generateKaobaReply` に decision_key / factors / trace 注入 |
| Conversation | Python `reason_builder` が explain.reason を優先 |
| Explain Payload 最終 | `meta.kaoba_ready` + `kaoba_intent` · sample に `kaoba_explain_pick` |
| decision_trace 最終 | Phase 1–2 stages を Kaoba reply の「判断トレース」へ投影 |
| UI | race.html「KAOBAに◎の理由を聞く」· chat.html `?prompt=` 自動送信 |

---

## Flag OFF 恒等性

| 確認 | 結果 |
|------|------|
| context なし + explain あり → explain_pick 注入なし | PASS |
| reason なし + v2_explain ON → 注入なし | PASS |
| beta.json `v2_explain: false` | PASS |
| Phase 1–2 契約 / E2E 回帰 | PASS |

---

## 契約テスト結果

```text
node --test tests/contract/explain-v2-phase3-kaoba.test.mjs \
  tests/contract/explain-v2.test.mjs tests/contract/kaoba.test.mjs
→ 25 passed

node --test tests/contract/explain-v2-e2e.test.mjs
→ 11 passed

python … test_explain*.py → 6 passed
```

---

## Explain Payload サンプル / スクショ

- `fixtures/explain/v2-explain-phase3-sample.json`
- `fixtures/explain/v2-explain-phase3-preview.html` / `.png`

---

## 変更ファイル一覧

| ファイル | 内容 |
|----------|------|
| `functions/_lib/explainPick.js` | **新規** explain_pick 投影 |
| `functions/_lib/kaobaDomain.js` | explain_pick 注入 · Flag ゲート |
| `functions/_lib/explainBuilder.js` | `kaoba_ready` meta |
| `services/.../reason_builder.py` | explain 2.1 優先 |
| `public/assets/api/prediction-bind.js` | KAOBA CTA |
| `public/chat.html` | `v2_explain` context · prompt 自動送信 |
| `public/assets/screens.css` | CTA スタイル |
| `tests/contract/explain-v2-phase3-kaoba.test.mjs` | Phase 3 契約テスト |
| `fixtures/explain/v2-explain-phase3-*` | サンプル / プレビュー |
| `docs/ops/v2-explainability-phase3-report.md` | 本レポート |
| `docs/releases/v2-explainability-final-report.md` | Final Report |
| `docs/releases/v2-explainability-design-review.md` | チェック完了 |
