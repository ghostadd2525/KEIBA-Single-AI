"""
AnalysisAdapter (Python)

契約: expect-analysis/1.0（変更禁止）
キー: PredictionBundle.race_id
現行: analysis.json mock
移行: RealAiAnalysisSource.get を実装
"""
from __future__ import annotations

import os
from typing import Any

from .. import data, domains

_DEFAULT = {
    "charts": [
        {"key": "pedigree", "label": "血統", "value": 70},
        {"key": "pace", "label": "展開", "value": 68},
        {"key": "jockey", "label": "騎手", "value": 66},
        {"key": "form", "label": "近走", "value": 67},
        {"key": "odds", "label": "オッズ", "value": 64},
    ],
    "overall": 70,
    "narrative": "データ準備中のレースです。",
}


class MockAnalysisSource:
    def get(self, race_id: str) -> dict[str, Any]:
        all_rows = data.load_analysis_all()
        row = all_rows.get(race_id) or {"race_id": race_id, **_DEFAULT}
        return domains.to_analysis(row, race_id)


class RealAiAnalysisSource:
    """実AI用プレースホルダ。未実装時は Mock へフォールバック。"""

    def __init__(self, fallback: MockAnalysisSource | None = None) -> None:
        self._fallback = fallback or MockAnalysisSource()

    def get(self, race_id: str) -> dict[str, Any]:
        # TODO: real feature/model → expect-analysis/1.0
        return self._fallback.get(race_id)


def _engine() -> str:
    return (os.environ.get("AI_ENGINE") or "mock").lower()


class AnalysisAdapter:
    def __init__(self) -> None:
        mock = MockAnalysisSource()
        self._source = RealAiAnalysisSource(mock) if _engine() == "real" else mock

    def get(self, race_id: str) -> dict[str, Any]:
        return self._source.get(race_id)


_adapter = AnalysisAdapter()


def get_analysis(race_id: str) -> dict[str, Any]:
    return _adapter.get(race_id)
