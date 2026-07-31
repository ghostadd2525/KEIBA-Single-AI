# Version49 — Mapper Audit

**Date:** 2026-07-28  
**Type:** Audit only  
**Mapper:** `prediction_response_to_bundle`（`single_prediction_mapper.py`）  
**Pre-mapper loss:** `predict_ranking` / `prediction_response` 組み立て

## ③ Mapper Audit — 削除 / 変換 / None 化

### Stage 0 — 到達前（Mapper 入力に元々無い）

| 項目 | 状態 | 根拠 |
|---|---|---|
| CE `world` / `sub_world` | Mapper 入力に存在しない | `predict` が `predict_ranking` のみ使用 |
| CE `meta` | 同上 | RankingResult に meta 無し |
| CE 行 `WorldMeta` | 同上 | `_ranking_rows_from_ce` が name/number/rank/score のみ |
| Pool / Role / Required | 全経路非保持 | V48 |

### Stage 1 — `predict_ranking` 投影（Facade）

| 入力（CE） | 出力（RankingResult） | 操作 |
|---|---|---|
| candidates[].Rank | ranking[].rank | 変換 |
| candidates[].Confidence | ranking[].score | **改名（Confidence→score）** |
| candidates[].CandidateID | horse_name | 改名 |
| HorseNumber | horse_number | 通過 |
| world / sub_world / meta / WorldMeta | — | **削除** |
| context（一部） | feature_source のみ | 部分通過 |

### Stage 2 — `prediction_response`（Single models）

| 入力 | 出力 | 操作 |
|---|---|---|
| RankingResult | `ranking` 配列のみ抽出 | ネスト剥がし |
| ConfidenceResult | overall/per_horse/factors のみ | キーフィルタ |
| world | フィールド無し | 非存在 |
| bets slips | items | 通過 |

### Stage 3 — `prediction_response_to_bundle`（本 Mapper）

| 項目 | 操作 | コード |
|---|---|---|
| `evaluation.world` | **None 固定** | L410 |
| `evaluation.sub_world` | **None 固定** | L411 |
| ranking[].score | runners[].**win_prob** へ変換 | `_runners_from_ranking` L228（実体は Confidence） |
| ranking[].rank | model_rank + mark(honmei/…) | `_MARK_BY_RANK` |
| confidence.overall | ai_confidence.score | 変換 |
| confidence.factors | ai_confidence.factors / explain bullets | 部分利用 |
| CE / Single explain_payload | **不使用** | 独自 `explain` 再生成 |
| CE meta | **不使用** | race_info は catalog/race_meta から |
| bets items | betting_recommendations | 構造変換 |
| schema | `single-prediction-bundle/2.0` 強制 | normalize |

### Stage 4 — `normalize_prediction_bundle`

| 操作 | 内容 |
|---|---|
| 欠落ブロック補完 | evaluation / ai_confidence / explain / betting の default |
| schema_version 上書き | BUNDLE_SCHEMA |
| world 復元 | **しない**（evaluation をそのまま維持 → None のまま） |

---

## Mapper Summary Table

| 情報 | Mapper での運命 |
|---|---|
| World | **Hardcoded None**（到達していても落とす設計。実経路では到達不能） |
| SubWorld | **Hardcoded None** |
| Meta（CE） | 未入力 → 不在 |
| Rank | model_rank として保持 |
| Confidence | score→win_prob へ **意味ラベル変換**（値は Confidence） |
| Explain Core | 破棄（別 explain を新規作成） |
| Betting | Single slips → Bundle recommendations |

## Note

Mapper コメント: 「契約スキーマは変更しない。Product 応答 dict を Expect 契約形へ投影するだけ。」  
→ 投影先スキーマに World 必須が無い / 明示 None であり、**CE World の伝播は契約外**として実装されている。
