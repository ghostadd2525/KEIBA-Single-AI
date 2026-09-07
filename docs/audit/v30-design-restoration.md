# Version30 — Design Restoration Audit

**Date:** 2026-07-27  
**Scope:** Research / Audit only（Prediction / PE / CE / AI / World / SubWorld / Role / Trigger / Challenge / ResultAutomation / Production — 変更禁止）  
**Predecessor:** V28 Difficulty Signal Audit · V29 World Signal Lineage Audit  

## Verdict (summary)

**B — Further Investigation Required**

設計式 `add_win5_leg_difficulty_features` は削除されていない。  
現経路から外れている主因は「FeatureGenerator からの呼び出し削除」ではなく、**(1) Core FG が元々 probability 境界のみを委任していること**と、**(2) 2026-07-25 以降の daily FeatureLoader CSV が pace/leg 系 46 列を失ったこと**の複合である。  
「FG へ戻す」だけでは復元ロケーションが確定せず、安全判定に未解決項目が残る。

---

## ① History — `add_win5_leg_difficulty_features`

### 実装時期・所在

| Item | Evidence |
|------|----------|
| Canonical module | `C:\win5-ai\demo_pace_model_v2.py`（同型: `pace_model_v2.py`） |
| Module docstring | 「races.csv から win5_leg を補完」「win5_leg を使ったレース難易度特徴量を追加」 |
| Production EC2 | `/opt/expect-ai/platform/demo_pace_model_v2.py` **不在** |
| Core overlay | `ai_platform.core.features.FeatureGenerator` に参照なし |

実装は Win5 オフライン pace バッチ側。Core デプロイ面には関数本体が無い。

### 呼び出し元（現存）

| Caller | Path | Role |
|--------|------|------|
| `build_pace_features()` | `demo_pace_model_v2.py` | **唯一の直接呼び出し** |
| `main_ai_v2.py` | `run_python_file("demo_pace_model_v2.py")` | 日次 AI パイプライン |
| `demo_daily_repick_history_pipeline.py` | `from demo_pace_model_v2 import build_pace_features` | 履歴パイプライン |
| bots / phase scripts | `auto_demo_42_5_bot_with_training.py` 等 | 運用スクリプト |

下流: `demo_merge_market_into_pace.py` が `demo_runners_pace_features.csv` → `demo_runners_pace_market_features.csv` へマージ。

### FeatureGenerator / probability 経路

`FeatureGenerator` docstring（Core overlay, commit `2e087fa` 2026-07-20）:

> boundary adapter only. It delegates to the functions used by `demo_win5_probability_calculator.py` and does not introduce feature logic.

実体:

1. `enrich_stable_features`
2. `ensure_style_count_features`
3. `prepare_feature_matrix`（凍結 28 列）

`demo_win5_probability_calculator` / `demo_probability_feature_utils` も **`add_win5_leg_difficulty_features` を呼ばない**。  
欠損時は `STABLE_FEATURE_DEFAULTS['race_leg_difficulty']=0.5`。

### 「現在未呼び出し」の分類

| Hypothesis | Judgment | Evidence |
|------------|----------|----------|
| 削除された | **No** | 関数・`build_pace_features` 呼び出しは win5-ai ルートに残存 |
| FeatureGenerator からのリファクタ漏れ（かつて FG にあった） | **Unsupported** | FG 導入時点から probability 委任のみ。Git 上 FG に当該呼出の痕跡なし |
| 意図的停止（Trigger 向けに止めた） | **No evidence** | Trigger/World を止めるコメント・フラグなし |
| アーキ境界ギャップ（設計式は pace バッチ、Core は CSV 列依存） | **Yes（主因）** | 設計マップ: history → pace_model_v2 → market merge → Ranker/World（`feature_dependency_map.md`） |
| daily CSV スキーマ縮退による列欠落 | **Yes（現 Production 直因）** | 下記 Daily CSV 節 |

### Daily CSV 遷移（Production 直因）

FeatureLoader 優先順: **daily CSV → global CSV**。

| Source | `race_leg_difficulty` | Notes |
|--------|:---------------------:|-------|
| Local daily ≤2026-06-28 | Yes（典型 116 列） | 設計式由来列あり（`leg_*`, `pace_collapse_risk`, `style_entropy`） |
| Local daily 2026-07-25 | **No**（72 列） | 旧比 −46 列（difficulty / pace / pre_world seeds 等） |
| EC2 daily 2026-07-25 / 07-26 | **No**（72–74 列） | Production 当日入力 |
| EC2 global `demo_runners_pace_market_features.csv` | Yes（116 列） | daily が勝つため通常未使用 |
| EC2 daily に sibling `demo_runners_pace_features.csv` | 不在 | pace 中間成果物が daily に無い |

旧 daily での実測（2026-06-28）: `race_leg_difficulty` unique_n=5, min≈0.43, max≈0.60, std≈0.062（定数 0.5 ではない）。

pi-keibanet `features.py` は **history 移植**で `build_features` を提供。`add_win5_leg_difficulty_features` 非含有。docstring の「legacy exact」と 2026-07-25 以降 daily の実列集合は一致しない（要追調査）。

### History 結論

```text
設計式の所在: offline pace_model_v2（削除されていない）
Core FG: 当初から未呼び出し（probability 境界）
想定接続: pace CSV 列として FeatureLoader が運ぶ
現断絶点: daily FeatureLoader CSV が race_leg_difficulty 等を欠く
          → enrich_stable_features が 0.5 を充填（V29 証明）
```

---

## ④ Compatibility（要約）

影響モジュール一覧の詳細は `v30-risk-assessment.md`。  
PE / CE / World Trigger / SubWorld / Role / Candidate Pool / Research が入力変化の対象。chaos 断絶は本復元では閉じない。

## Cross-links

- `docs/audit/v30-dependency-audit.md`
- `docs/audit/v30-contract-gap.md`
- `docs/audit/v30-risk-assessment.md`
- `docs/audit/v30-restoration-readiness.md`
- V29: `docs/audit/v29-signal-lineage.md`, `v29-default-value-audit.md`

## Guardrails

- 本ドキュメントは監査のみ。復元実装・閾値変更・Trigger 変更なし。
