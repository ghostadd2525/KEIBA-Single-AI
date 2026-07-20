# -*- coding: utf-8 -*-
"""mock_fallback 理由コード（運用 meta 用。PredictionBundle 契約外）."""
from __future__ import annotations

from typing import Final

# 安定した理由コード（API / ログ / missing report で共通）
FALLBACK_REASONS: Final[tuple[str, ...]] = (
    "platform_missing",  # ai_platform 未配置 / AI_PLATFORM_ROOT 不正
    "race_not_found",  # Core race index に無い
    "feature_csv_missing",  # 特徴量 CSV ファイル自体が無い
    "market_feature_missing",  # runners_pace_market_features 行が無い
    "feature_missing",  # その他特徴量不足
    "model_not_loaded",  # モデル/パイプライン未ロード
    "prediction_failed",  # get_prediction が error / None
    "timeout",  # 将来用
    "exception",  # 予期しない例外
    "unknown",
)

REASON_HELP: Final[dict[str, str]] = {
    "platform_missing": "AI_PLATFORM_ROOT に ai_platform を配置し PYTHONPATH を通す",
    "race_not_found": "data/races.csv（または DB races）に date/venue/race_no を追加",
    "feature_csv_missing": "runners_pace_market_features.csv 等を data/ に配置",
    "market_feature_missing": "当該 core_race_id の特徴量行を CSV/DB features に追加",
    "feature_missing": "不足特徴量カラムを埋める",
    "model_not_loaded": "CorePipeline / 依存 demo_* モジュールを確認",
    "prediction_failed": "Core 推論エラー内容を logs で確認",
    "timeout": "タイムアウト設定・データ量を見直す",
    "exception": "スタックトレースを logs で確認",
    "unknown": "診断を再実行し詳細ログを確認",
}
