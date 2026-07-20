"""
PredictionAdapter (Python)

契約: single-prediction-bundle/2.0（変更禁止）
現行: Mock JSON（public/data/mocks）
移行: RealAiPredictionSource → Single AI 実推論 → PredictionBundle 投影

運用メタ（envelope）:
  list/get は Bundle と分離した provenance を返す（PB 本体は変更しない）。
"""
from __future__ import annotations

import os
from typing import Any

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
    return {
        "service": "PredictionService",
        "adapter": "PredictionAdapter",
        "provider": "python",
        "engine": engine,
        "engine_source": item.get("engine_source"),
        "model_version": item.get("model_version"),
        "inference_generated_at": item.get("inference_generated_at"),
        **({"core_race_id": item["core_race_id"]} if item.get("core_race_id") else {}),
        "race_id": item.get("race_id"),
    }


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
    Core が解決できない race_id は Mock へフォールバック。
    """

    def __init__(self, fallback: MockPredictionSource | None = None) -> None:
        self._fallback = fallback or MockPredictionSource()

    def _catalog_race(self, race_id: str) -> dict[str, Any] | None:
        catalog = data.load_races()
        for race in catalog.get("races") or []:
            if str(race.get("race_id") or "") == race_id:
                return race
        return None

    def _infer_bundle(
        self,
        public_race_id: str,
        race_meta: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        if not mapper.ensure_ai_platform_path():
            return None, None
        try:
            core_id = mapper.resolve_core_race_id(public_race_id, race_meta)
            if not core_id:
                return None, None
            response = mapper.run_single_prediction(core_id)
            if not response:
                return None, None
            bundle = mapper.prediction_response_to_bundle(
                response,
                public_race_id=public_race_id,
                core_race_id=core_id,
                race_meta=race_meta,
            )
            return bundle, core_id
        except Exception:
            return None, None

    def _mock_one(self, rid: str, race: dict[str, Any] | None) -> dict[str, Any]:
        specific = data.MOCK_DIR / f"bundle-{rid}.json"
        if specific.exists():
            return domains.normalize_prediction_bundle(data.load_bundle(rid), rid)
        template = data.load_bundle("20260719_hanshin_11")
        if race:
            return domains.catalog_to_prediction_bundle(race, template)
        fb, _ = self._fallback.get_with_meta(rid)
        return fb  # type: ignore[return-value]

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
            real, core_id = self._infer_bundle(rid, race_meta=race)
            if real:
                items.append(real)
                prov.append(provenance_item(real, "real_ai", core_race_id=core_id))
            else:
                bundle = self._mock_one(rid, race)
                items.append(bundle)
                prov.append(provenance_item(bundle, "mock_fallback"))
        return items, list_meta("real", prov)

    def get_with_meta(self, race_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        rid = str(race_id or "").strip()
        if not rid:
            return None, None
        real, core_id = self._infer_bundle(rid, race_meta=self._catalog_race(rid))
        if real:
            item = provenance_item(real, "real_ai", core_race_id=core_id)
            return real, get_meta("real", item)
        bundle = self._fallback.get_bundle(rid)
        if not bundle:
            return None, None
        item = provenance_item(bundle, "mock_fallback")
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
