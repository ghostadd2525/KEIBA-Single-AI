"""
PredictionAdapter (Python)

契約: single-prediction-bundle/2.0（変更禁止）
現行: Mock JSON（public/data/mocks）
移行: RealAiPredictionSource → Single AI 実推論 → PredictionBundle 投影

運用メタ（envelope）:
  list/get は Bundle と分離した provenance を返す（PB 本体は変更しない）。
  mock_fallback 時は fallback_reason を付与する。
"""
from __future__ import annotations

import os
from typing import Any

from ...diagnostics.logging_ops import log_fallback_event
from ...diagnostics.missing_collector import collect_missing_report
from .. import data, domains
from . import single_prediction_mapper as mapper


def _engine() -> str:
    raw = (os.environ.get("AI_ENGINE") or "mock").lower()
    return "real" if raw == "real" else "mock"


def _core_race_id_from_bundle(bundle: dict[str, Any] | None) -> str | None:
    if not bundle:
        return None
    meta = ((bundle.get("explain") or {}).get("meta") or {})
    cid = meta.get("core_race_id")
    return str(cid) if cid else None


def provenance_item(
    bundle: dict[str, Any],
    engine_source: str,
    *,
    core_race_id: str | None = None,
    fallback_reason: str | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "race_id": bundle.get("race_id"),
        "engine_source": engine_source,
        "model_version": bundle.get("model_version"),
        "inference_generated_at": bundle.get("generated_at"),
    }
    cid = core_race_id or _core_race_id_from_bundle(bundle)
    if cid:
        item["core_race_id"] = cid
    if engine_source == "mock_fallback" and fallback_reason:
        item["fallback_reason"] = fallback_reason
    if detail:
        item["detail"] = detail
    return item


def list_meta(engine: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "service": "PredictionService",
        "adapter": "PredictionAdapter",
        "provider": "python",
        "engine": engine,
        "items": items,
    }


def get_meta(engine: str, item: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "service": "PredictionService",
        "adapter": "PredictionAdapter",
        "provider": "python",
        "engine": engine,
        "engine_source": item.get("engine_source"),
        "model_version": item.get("model_version"),
        "inference_generated_at": item.get("inference_generated_at"),
        "race_id": item.get("race_id"),
    }
    if item.get("core_race_id"):
        meta["core_race_id"] = item["core_race_id"]
    if item.get("fallback_reason"):
        meta["fallback_reason"] = item["fallback_reason"]
    if item.get("detail"):
        meta["detail"] = item["detail"]
    return meta


class MockPredictionSource:
    """現行: fixtures / mocks から PredictionBundle を組み立てる。"""

    def list_with_meta(self, date: str = "", venue: str = "") -> tuple[list[dict[str, Any]], dict[str, Any]]:
        catalog = data.load_races()
        races = list(catalog.get("races") or [])
        if date:
            races = [r for r in races if r.get("date") == date]
        if venue and venue != "すべて":
            races = [r for r in races if r.get("venue") == venue]

        template = data.load_bundle("20260719_hanshin_11")
        items: list[dict[str, Any]] = []
        prov: list[dict[str, Any]] = []
        for race in races:
            rid = str(race.get("race_id") or "")
            specific = data.MOCK_DIR / f"bundle-{rid}.json"
            if specific.exists():
                full = data.load_bundle(rid)
                bundle = domains.normalize_prediction_bundle(full, rid)
            else:
                bundle = domains.catalog_to_prediction_bundle(race, template)
            items.append(bundle)
            prov.append(provenance_item(bundle, "mock"))
        return items, list_meta("mock", prov)

    def get_with_meta(self, race_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        raw = data.load_bundle(race_id)
        if not raw:
            return None, None
        bundle = domains.normalize_prediction_bundle(raw, race_id)
        item = provenance_item(bundle, "mock")
        return bundle, get_meta("mock", item)

    def list_bundles(self, date: str = "", venue: str = "") -> list[dict[str, Any]]:
        items, _ = self.list_with_meta(date=date, venue=venue)
        return items

    def get_bundle(self, race_id: str) -> dict[str, Any] | None:
        bundle, _ = self.get_with_meta(race_id)
        return bundle


class RealAiPredictionSource:
    """
    Single AI 実推論 → PredictionBundle。
    Core が解決できない race_id は Mock へフォールバックし fallback_reason を付与。
    """

    def __init__(self, fallback: MockPredictionSource | None = None) -> None:
        self._fallback = fallback or MockPredictionSource()

    def _catalog_race(self, race_id: str) -> dict[str, Any] | None:
        catalog = data.load_races()
        for race in catalog.get("races") or []:
            if str(race.get("race_id") or "") == race_id:
                return race
        return None

    def _mock_one(self, rid: str, race: dict[str, Any] | None) -> dict[str, Any]:
        specific = data.MOCK_DIR / f"bundle-{rid}.json"
        if specific.exists():
            return domains.normalize_prediction_bundle(data.load_bundle(rid), rid)
        template = data.load_bundle("20260719_hanshin_11")
        if race:
            return domains.catalog_to_prediction_bundle(race, template)
        fb, _ = self._fallback.get_with_meta(rid)
        return fb  # type: ignore[return-value]

    def _infer(
        self,
        rid: str,
        race: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        diag = mapper.diagnose_inference(rid, race_meta=race)
        if diag.get("ok") and diag.get("bundle"):
            bundle = diag["bundle"]
            item = provenance_item(
                bundle,
                "real_ai",
                core_race_id=diag.get("core_race_id"),
            )
            return bundle, item

        bundle = self._mock_one(rid, race)
        reason = str(diag.get("fallback_reason") or "unknown")
        item = provenance_item(
            bundle,
            "mock_fallback",
            core_race_id=diag.get("core_race_id"),
            fallback_reason=reason,
            detail=diag.get("detail"),
        )
        log_fallback_event(
            race_id=rid,
            engine_source="mock_fallback",
            fallback_reason=reason,
            core_race_id=diag.get("core_race_id"),
            detail=diag.get("detail"),
        )
        return bundle, item

    def list_with_meta(self, date: str = "", venue: str = "") -> tuple[list[dict[str, Any]], dict[str, Any]]:
        catalog = data.load_races()
        races = list(catalog.get("races") or [])
        if date:
            races = [r for r in races if r.get("date") == date]
        if venue and venue != "すべて":
            races = [r for r in races if r.get("venue") == venue]

        items: list[dict[str, Any]] = []
        prov: list[dict[str, Any]] = []
        for race in races:
            rid = str(race.get("race_id") or "")
            bundle, item = self._infer(rid, race)
            items.append(bundle)
            prov.append(item)

        meta = list_meta("real", prov)
        try:
            report = collect_missing_report(prov)
            meta["missing_report"] = {
                "summary": report.get("summary"),
                "paths": report.get("paths"),
            }
        except Exception as exc:
            meta["missing_report_error"] = str(exc)
        return items, meta

    def get_with_meta(self, race_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        rid = str(race_id or "").strip()
        if not rid:
            return None, None
        bundle, item = self._infer(rid, self._catalog_race(rid))
        return bundle, get_meta("real", item)

    def list_bundles(self, date: str = "", venue: str = "") -> list[dict[str, Any]]:
        items, _ = self.list_with_meta(date=date, venue=venue)
        return items

    def get_bundle(self, race_id: str) -> dict[str, Any] | None:
        bundle, _ = self.get_with_meta(race_id)
        return bundle


class PredictionAdapter:
    def __init__(self) -> None:
        mock = MockPredictionSource()
        self._source = RealAiPredictionSource(mock) if _engine() == "real" else mock

    def list_with_meta(self, date: str = "", venue: str = "") -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return self._source.list_with_meta(date=date, venue=venue)

    def get_with_meta(self, race_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        return self._source.get_with_meta(race_id)

    def list_bundles(self, date: str = "", venue: str = "") -> list[dict[str, Any]]:
        return self._source.list_bundles(date=date, venue=venue)

    def get_bundle(self, race_id: str) -> dict[str, Any] | None:
        return self._source.get_bundle(race_id)


_adapter = PredictionAdapter()


def list_bundles(date: str = "", venue: str = "") -> list[dict[str, Any]]:
    return _adapter.list_bundles(date=date, venue=venue)


def get_bundle(race_id: str) -> dict[str, Any] | None:
    return _adapter.get_bundle(race_id)


def list_with_meta(date: str = "", venue: str = "") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return _adapter.list_with_meta(date=date, venue=venue)


def get_with_meta(race_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    return _adapter.get_with_meta(race_id)
