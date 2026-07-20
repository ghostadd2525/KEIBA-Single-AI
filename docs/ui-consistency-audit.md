# UI Consistency Audit

実施日: 2026-07-20  
対象: `KEIBA-Single-AI/public` Web UI ↔ Prediction / Conversation / Data Supply API

---

## 1. UI ↔ API 対応表

| UI 表示 | API フィールド | 画面 | 修正前 | 修正後 |
|---------|----------------|------|--------|--------|
| 本命馬番・馬名 | `evaluation.runners[mark=honmei]` | race.html | ○ | ○ |
| 対抗・穴・中穴 | `evaluation.runners[mark=taikou/ana/chuuken]` | race.html | ✗ 未表示 | ○ 印・pick cards |
| 表示順位 | `evaluation.runners[].model_rank` | race.html | ✗ 未使用 | ○ 印チップに rank 表示 |
| AI信頼度 % | `ai_confidence.score` | race.html, index | ○ | ○（別計算なし） |
| 信頼度 band | `ai_confidence.band` | race.html | ✗ | ○ 本命カード + 詳細 |
| 信頼度 factors | `ai_confidence.factors` | race.html | ✗ | ○ 信頼度セクション |
| 展開 narrative | `explain.narrative` | race.html | ○ | ○ |
| 理由 bullets | `explain.reasons[]` | race.html | ✗ | ○ 理由セクション |
| 買い目 | `betting_recommendations.items[]` | strategy.html | ✗ ハードコード | ○ API 優先 |
| engine_source | envelope `meta.engine_source` | race.html | ✗ | ○ provenance bar |
| feature_source | `meta.feature_source` | race.html, mypage | ✗ | ○ provenance + coverage |
| fallback_reason | `meta.fallback_reason` | race.html | ✗ | ○ provenance bar |
| core_race_id | `meta.core_race_id` | race.html | ✗ | ○ provenance + mismatch 警告 |
| Conversation reply | `reply` | chat.html | ○ (Kaoba only) | ○ Conversation 優先 |
| sections | `sections[]` | chat.html | ✗ | ○ HTML 表示 |
| context | `context` | chat.html | ✗ | ○ JSON 表示 |
| sources | `sources[]` | chat.html | ✗ | ○ リスト表示 |
| coverage | `/v1/data/coverage` | mypage | ✗ | ○ Supply パネル |
| diagnostics | `/v1/diagnostics/missing` | mypage | ✗ | ○ Supply パネル |

---

## 2. 一致している項目（修正後）

- **PredictionBundle 契約**: `schema_version`, `race_id`, `race_info`, `evaluation.runners`, `ai_confidence.score`, `explain.narrative`
- **信頼度**: `ai_confidence.score` を `scorePercent()` で ×100 表示（Analysis への混同なし）
- **Race Resolver**: URL `race_id` と bundle `race_id` 不一致時に警告カード
- **Buy Advice**: `strategy.html` が `betting_recommendations` + 印（taikou/ana）から構築
- **Conversation**: `chat.html` が Conversation API → Kaoba フォールバック

---

## 3. 一致していなかった項目（修正前）

| # | 問題 | 影響 |
|---|------|------|
| 1 | envelope `meta` を UI が破棄 | mock / real_ai 判別不可 |
| 2 | 印・理由・買い目が本番 race.html 未表示 | PB の大半が未使用 |
| 3 | chat が Kaoba のみ | Conversation Layer 未接続 |
| 4 | Coverage / Diagnostics UI なし | 運用 KPI 不可視 |
| 5 | strategy.html ハードコード | SingleAI 馬券ロジックと乖離 |
| 6 | 展開ドット静的 | model_rank Top5 未反映 |
| 7 | `app.js` が契約準拠だが未配線 | 二重実装 |

---

## 4. 残存ギャップ / 改善案

| 項目 | 状態 | 改善案 |
|------|------|--------|
| 星表示 (★5) | `score/20` で UI 再計算 | band 連動 or API に stars 追加 |
| Analysis 評価内訳 | Analysis API 依存（PB 外） | component_scores 投影を検討 |
| 一覧ソート | 信頼度降順（UI 側） | model_rank 順オプション追加 |
| admin 専用画面 | mypage に簡易パネルのみ | `/admin/dashboard` 専用 UI |
| `real_ai_rate` 数値 | coverage に mock 時は未算出 | core_validation 連携 API |
| context JSON 生表示 | デバッグ向け | 本番は折りたたみ UI に |

---

## 5. 変更ファイル

- `public/assets/api/prediction.js` — `getWithMeta`, `__meta` 保持
- `public/assets/api/prediction-bind.js` — 印・理由・provenance・pace dots
- `public/assets/api/conversation.js` — 新規
- `public/assets/api/supply.js` — 新規
- `public/race.html`, `chat.html`, `strategy.html`, `mypage.html`
- `public/assets/ux.css`
- `functions/api/data/coverage.js`, `functions/api/diagnostics/fallback-reasons.js`
- `functions/_lib/adapters/predictionAdapter.js`
- `services/win5-ai/app/engine/adapters/prediction_adapter.py`

---

## 6. 検証手順

```bash
# レース詳細 — 印・provenance・race_id 警告
open race.html?race_id=20260719_hanshin_11

# Conversation — sections/context/sources
open chat.html?race_id=20260719_hanshin_11

# 買い目 — betting_recommendations
open strategy.html?race_id=20260719_hanshin_11

# Coverage — mypage Supply パネル
open mypage.html
```
