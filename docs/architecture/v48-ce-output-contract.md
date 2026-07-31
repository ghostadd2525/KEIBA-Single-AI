# Version48 — CE Output Contract

**Date:** 2026-07-28  
**Type:** Audit only

## ③ Output Contract — 経路別

### A. Canonical: `evaluate_candidates` → CorePublicBundle

| フィールド | 内容 |
|---|---|
| `race_id` | レース ID |
| `candidates[]` | `CandidateID`, `Rank`, `Confidence`, `HorseNumber`, `WorldMeta`, `SubWorldMeta` |
| `context` | source, feature_source, feature_metadata, field_size |
| `world` / `sub_world` | レースラベル |
| `overall_confidence` / `confidence_factors` | 信頼度 |
| `meta` | detect_race_meta 全文 |
| `core_version` | 固定文字列 |
| `explain_payload` | Flag ON 時のみ |

### B. Compatibility views（Facade 投影）

| API | 公開する | **破棄する** |
|---|---|---|
| `predict_ranking` | race_id, ranking monogram (name/number/rank/**score=Confidence**), core_version, feature_source | **world, sub_world, meta, WorldMeta, explain, raw scores** |
| `predict_confidence` | overall, per_horse, factors, core_version | world, ranking 詳細, meta |
| `resolve_core` | world, sub_world, ranking, confidence, meta, context, core_version; `features=None` | CE 行の WorldMeta は ranking 投影に無く name/rank/score のみ。raw PE scores なし |

### C. Consumer-specific outputs

#### Prediction / Single（HTTP `/v1/predictions`）

経路: `predict` → `predict_ranking` + `predict_confidence` →（Adapter）`prediction_response_to_bundle`

| 公開 | 破棄・固定 |
|---|---|
| runners: model_rank, win_prob（mapper 側再構成）, marks | **`evaluation.world = None`**, **`sub_world = None`** |
| ai_confidence | CE meta / world 非伝播 |
| explain（mapper 独自） | Core `explain_payload` 非使用（別組み立て） |
| betting_recommendations | ranking 由来 |

出典: `single/prediction/__init__.py` L33–40; `single_prediction_mapper.py` L408–412。

#### Win5

| 経路 | CE 利用 |
|---|---|
| `demo_ticket_optimizer_core`（Pool/Ticket） | **`evaluate_candidates` 非呼出** |
| 結論 | Win5 購入経路は **CE Output Contract の消費者ではない**（別レガシー契約） |

#### GUI / Ops UI

| 経路 | 実体 |
|---|---|
| 予測表示 | 主に PredictionBundle（world=None） |
| Research 監査 | 直接 `evaluate_candidates` / `resolve_core` を呼ぶ場合あり（例: signal_lineage_audit） |

#### Explain

| 経路 | 内容 |
|---|---|
| Core `explain_payload` | CE Bundle 内。Flag 既定 OFF なら **キー省略** |
| Single Bundle `explain` | mapper が ranking/confidence から再生成。**CE world を読まない** |

---

## Output Contract Matrix

| 出力面 | Rank | Confidence | World | SubWorld | meta | Pool/Role/Required | win_prob raw |
|---|---|---|---|---|---|---|---|
| CorePublicBundle | Yes | Yes | Yes | Yes | Yes | No | No（行に無し） |
| predict_ranking | Yes | as score | **No** | **No** | **No** | No | No |
| resolve_core | Yes | Yes | Yes | Yes | Yes | No | No |
| PredictionBundle | Yes | Yes | **None** | **None** | 部分(race_info) | No | mapped |
| Win5 optimizer | — | — | 独自分類 | 独自 | 独自 | Yes（自前） | 自前 |

## Contract Statement

```text
Canonical CE Output INCLUDES world/sub_world/meta.
Primary Prediction path DOES NOT publish them.
→ Public contract is path-dependent (structural fracture).
```
