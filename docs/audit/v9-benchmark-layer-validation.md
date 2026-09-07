# Version9.0 Audit — Benchmark Layer Validation

**Date:** 2026-07-27  
**Scope:** Challenge Benchmark Layer only（PE / CE / AI推論 / Research / ResultAutomation 非変更）  
**Result:** **PASS**

---

## 1. 検証環境

| 項目 | 値 |
|------|-----|
| AI DB | EC2 `expect_ai.db`（本番） |
| 対象月 | `2026-07`（51R） |
| Unit | `tests/challenge/test_v9_benchmark_layer.py` → 6/6 OK |
| Live | `tmp-v9-validate.py` on EC2 → all checks PASS |

---

## 2. チェックリスト

| # | 要件 | 結果 | 根拠 |
|---|------|:----:|------|
| 1 | AI Benchmark が単勝になること | **PASS** | Flag ON: `book.bet_types=["単勝"]`, profit **-2,560**, recovery **50%**, hit **16%**, races **51** |
| 2 | User Challenge に影響しないこと | **PASS** | Flag OFF/ON で `user.summary.profit` 同一（本検証 stub: 0） |
| 3 | Purchase Lab が表示できること（データ） | **PASS** | 5戦略: 三連単 / 馬連 / ワイド / 複勝 / 単勝＋複勝。`visible_by_default=false` |
| 4 | 比較バナーが benchmark を使用すること | **PASS** | `comparison.source="benchmark"`, `ai_profit === benchmark.summary.profit`（-2560） |
| 5 | Flag OFF で現行動作 | **PASS** | `ai` は 4券種、profit **-54,380**、`source=ai_legacy_book`、`benchmark`/`purchase_lab` キーなし |
| 6 | Ops Benchmark Strategy カード | **PASS** | `/ops-data/benchmark-strategy.json` + System グリッド描画 |

---

## 3. 実測サマリ（2026-07 / 51R）

| 層 | 利益 | 回収率 | 的中率 | 購入額 |
|----|-----:|-------:|-------:|-------:|
| Legacy AI（V8.9 / flag OFF） | -54,380 | 27% | 12% | 74,900 |
| **Benchmark ◎単勝（flag ON）** | **-2,560** | **50%** | **16%** | **5,100** |

旧分析（`docs/audit/challenge-ai-profit-analysis.md`）と一致。

---

## 4. Feature Flag

| 変数 | 既定 | 備考 |
|------|------|------|
| `V9_BENCHMARK_LAYER`（AI） | OFF | ON 時のみ V9 API 形状 |
| `V9_BENCHMARK_LAYER`（Pages `wrangler.toml`） | `"false"` | BFF meta ミラー |

**本番 UI 切替:** AI と Pages の両方で ON にしてから確認すること。現状デフォルト OFF のためユーザー向けは V8.9 表示のまま。

---

## 5. 変更ファイル（境界）

- `services/win5-ai/app/challenge/service.py`
- `services/win5-ai/app/challenge/__init__.py`
- `services/win5-ai/tests/challenge/test_v9_benchmark_layer.py`
- `functions/api/v1/challenge/monthly.js`
- `public/assets/api/challenge-dashboard.js`
- `public/saved.html` / `public/index.html` / `public/ops.html`
- `public/assets/screens.css`
- `public/assets/ops-console-v89.js`
- `public/ops-data/benchmark-strategy.json`
- `wrangler.toml`
- `docs/design/v9-benchmark-layer.md`
- `docs/audit/v9-benchmark-layer-validation.md`（本ファイル）

**未変更:** PE / CE / AI推論 / Research / ResultAutomation / Prediction Logic / `race_result_settle` 本体。

---

## 6. UI 確認メモ（Flag ON 時）

1. Challenge メインカードタイトルが「AI Benchmark（◎単勝1点）」
2. バナー利益が Benchmark（単勝）と一致
3. Purchase Lab は折りたたみ（`<details>`）でのみ開く
4. User カードは個人台帳のまま

---

## 7. 判定

**Overall: PASS** — Benchmark Layer 実装・互換・検証完了。本番ユーザー表示は Flag OFF 維持。
