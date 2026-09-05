# -*- coding: utf-8 -*-
"""
Race Resolver — UI表記 / catalog / core / slug の相互変換。

Prediction・Conversation・ETL は必ず本モジュール経由で race_id を解決する。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from .catalog_index import CatalogIndex, CatalogRace, get_catalog_index
from .race_refs import (
    CatalogRaceRef,
    CoreRaceRef,
    FeatureLookupRef,
    NumericRaceRef,
    VenueQualifiedRaceRef,
)
from .repository import RaceRepository

# ai_platform 由来の venue code（検証データ基準）
_VENUE_CODE_TO_JA: dict[str, str] = {
    "01": "札幌",
    "02": "函館",
    "03": "函館",
    "04": "福島",
    "05": "阪神",
    "06": "中山",
    "07": "中京",
    "08": "京都",
    "09": "東京",
    "10": "小倉",
}

_VENUE_JA_TO_CODE: dict[str, str] = {}
for code, ja in _VENUE_CODE_TO_JA.items():
    _VENUE_JA_TO_CODE.setdefault(ja, code)

_VENUE_JA_TO_EN: dict[str, str] = {
    "札幌": "sapporo",
    "函館": "hakodate",
    "福島": "fukushima",
    "新潟": "niigata",
    "東京": "tokyo",
    "中山": "nakayama",
    "中京": "chukyo",
    "京都": "kyoto",
    "阪神": "hanshin",
    "小倉": "kokura",
}

_VENUE_EN_TO_JA = {v: k for k, v in _VENUE_JA_TO_EN.items()}


def _load_env_venue_maps() -> None:
    raw = (os.environ.get("AI_VENUE_CODE_MAP") or "").strip()
    if not raw:
        return
    try:
        mapping = json.loads(raw)
        for code, ja in mapping.items():
            _VENUE_CODE_TO_JA[str(code).zfill(2)] = str(ja)
            _VENUE_JA_TO_CODE[str(ja)] = str(code).zfill(2)
    except json.JSONDecodeError:
        pass


_load_env_venue_maps()


@dataclass
class RaceIdentity:
    """解決済みレース ID の正規形。曖昧な race_id 文字列だけを持たない。"""

    date: str
    venue_ja: str
    race_no: int
    venue_code: str | None = None
    venue_en: str | None = None
    core_race_id: str | None = None
    catalog_race_id: str | None = None
    public_race_id: str | None = None
    source: str = "unknown"
    id_namespace: str = "unknown"
    numeric_race_id: str | None = None
    feature_lookup_key: str | None = None
    catalog_ref: CatalogRaceRef | None = None
    numeric_ref: NumericRaceRef | None = None
    core_ref: CoreRaceRef | None = None
    feature_lookup_ref: FeatureLookupRef | None = None
    race_row: dict[str, Any] | None = field(default=None, repr=False)

    def as_meta(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "venue": self.venue_ja,
            "race_no": self.race_no,
            "venue_code": self.venue_code,
            "core_race_id": self.core_race_id,
            "catalog_race_id": self.catalog_race_id,
            "public_race_id": self.public_race_id,
            "id_namespace": self.id_namespace,
            "numeric_race_id": self.numeric_race_id,
            "feature_lookup_key": self.feature_lookup_key,
        }


class RaceResolver:
    """任意表記 → RaceIdentity（双方向変換含む）。"""

    def __init__(
        self,
        repo: RaceRepository | None = None,
        catalog: CatalogIndex | None = None,
    ) -> None:
        self.repo = repo or RaceRepository()
        self._catalog_override = catalog

    def _catalog(self) -> CatalogIndex:
        return self._catalog_override or get_catalog_index()

    # --- public API ---

    def resolve(
        self,
        text_or_id: str,
        *,
        date_hint: str | None = None,
        race_meta: dict[str, Any] | None = None,
    ) -> RaceIdentity | None:
        raw = (text_or_id or "").strip()
        if not raw:
            return None

        parsed = self._parse(raw, date_hint=date_hint, race_meta=race_meta)
        if not parsed:
            return None

        parsed = self._bridge_from_catalog(parsed, raw)
        identity = self._hydrate(parsed)
        db_hit = self._lookup_db(identity)
        if db_hit:
            identity = self._merge_db(identity, db_hit)

        if not identity.core_race_id:
            identity.core_race_id = self._resolve_core_via_platform(identity)

        self._fill_derived_ids(identity)
        return identity

    def resolve_public_id(
        self,
        text_or_id: str,
        *,
        date_hint: str | None = None,
        race_meta: dict[str, Any] | None = None,
    ) -> str | None:
        ident = self.resolve(text_or_id, date_hint=date_hint, race_meta=race_meta)
        if not ident:
            return None
        return ident.public_race_id or ident.catalog_race_id or ident.core_race_id

    def resolve_core_id(
        self,
        text_or_id: str,
        *,
        date_hint: str | None = None,
        race_meta: dict[str, Any] | None = None,
    ) -> str | None:
        ident = self.resolve(text_or_id, date_hint=date_hint, race_meta=race_meta)
        return ident.core_race_id if ident else None

    def to_catalog(self, identity: RaceIdentity) -> str:
        return identity.catalog_race_id or f"{identity.date}-{identity.venue_ja}-{identity.race_no}"

    def to_core(self, identity: RaceIdentity) -> str | None:
        return identity.core_race_id

    def to_public(self, identity: RaceIdentity) -> str:
        if identity.public_race_id:
            return identity.public_race_id
        en = identity.venue_en or _VENUE_JA_TO_EN.get(identity.venue_ja, identity.venue_ja)
        d = identity.date.replace("-", "")
        return f"{d}_{en}_{identity.race_no}"

    def parse_ui_label(self, text: str, *, date_hint: str | None = None) -> RaceIdentity | None:
        m = re.search(
            r"(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)\s*(\d{1,2})\s*R?",
            text,
        )
        if not m:
            return None
        venue_ja, race_no = m.group(1), int(m.group(2))
        d = date_hint or self._infer_date_hint(text)
        if not d:
            return None
        return self.resolve(f"{d}-{venue_ja}-{race_no}")

    # --- parsing ---

    def _parse(
        self,
        raw: str,
        *,
        date_hint: str | None = None,
        race_meta: dict[str, Any] | None = None,
    ) -> RaceIdentity | None:
        meta = race_meta or {}

        # UI: 福島11R
        ui = re.search(
            r"(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)\s*(\d{1,2})\s*R?",
            raw,
        )
        if ui and not re.search(r"\d{4}-\d{2}-\d{2}", raw):
            d = date_hint or meta.get("date") or self._infer_date_hint(raw)
            if d:
                venue_ja = ui.group(1)
                return RaceIdentity(
                    date=str(d)[:10],
                    venue_ja=venue_ja,
                    race_no=int(ui.group(2)),
                    venue_en=_VENUE_JA_TO_EN.get(venue_ja),
                    venue_code=_VENUE_JA_TO_CODE.get(venue_ja),
                    source="ui_label",
                    id_namespace="ui_label",
                )

        # slug: 20260719_fukushima_11
        slug = re.fullmatch(r"(\d{8})_([a-z0-9]+)_(\d+)", raw.lower())
        if slug:
            d = f"{slug.group(1)[:4]}-{slug.group(1)[4:6]}-{slug.group(1)[6:8]}"
            en = slug.group(2)
            venue_ja = _VENUE_EN_TO_JA.get(en, meta.get("venue") or en)
            return RaceIdentity(
                date=d,
                venue_ja=str(venue_ja),
                race_no=int(slug.group(3)),
                venue_en=en,
                venue_code=_VENUE_JA_TO_CODE.get(str(venue_ja)),
                public_race_id=raw.lower(),
                source="slug",
                id_namespace="slug",
            )

        # venue-qualified: 2026-08-16-札幌-10
        venue_q = VenueQualifiedRaceRef.parse(raw)
        if venue_q:
            return RaceIdentity(
                date=venue_q.date,
                venue_ja=venue_q.venue_name,
                race_no=venue_q.race_no,
                venue_en=_VENUE_JA_TO_EN.get(venue_q.venue_name),
                venue_code=_VENUE_JA_TO_CODE.get(venue_q.venue_name),
                catalog_race_id=venue_q.as_id(),
                source="catalog",
                id_namespace="venue_qualified",
            )

        # JRA numeric: 202601010810
        numeric = NumericRaceRef.parse(raw)
        if numeric:
            hit = self._catalog().lookup_numeric(numeric.as_id())
            if hit:
                return self._identity_from_catalog(hit, raw=raw, id_namespace="numeric")

        # YYYY-MM-DD-NN-NN は Catalog (label_no) と Core (JRA venue) で同形。
        # 形式から namespace を推測しない。Catalog exact lookup を先に行う。
        dotted = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-(\d{2})-(\d+)", raw)
        if dotted:
            hit = self._catalog().lookup_catalog_id(raw)
            if hit:
                return self._identity_from_catalog(hit, raw=raw, id_namespace="catalog")
            # Catalog に無いときだけ legacy Core 入力として扱う。
            # meeting label を JRA venue と読まない — この枝は feature key 保存用。
            code = dotted.group(2).zfill(2)
            venue_ja = _VENUE_CODE_TO_JA.get(code, meta.get("venue") or code)
            core_id = f"{dotted.group(1)}-{code}-{int(dotted.group(3)):02d}"
            return RaceIdentity(
                date=dotted.group(1),
                venue_ja=str(venue_ja),
                race_no=int(dotted.group(3)),
                venue_code=code,
                venue_en=_VENUE_JA_TO_EN.get(str(venue_ja)),
                core_race_id=core_id,
                source="core",
                id_namespace="core",
                feature_lookup_key=core_id,
                core_ref=CoreRaceRef.parse(core_id),
                feature_lookup_ref=FeatureLookupRef.from_legacy_core(core_id),
            )

        # free text with embedded slug
        embedded = re.search(r"(20\d{6}_[a-z0-9]+_\d+)", raw.lower())
        if embedded:
            return self._parse(embedded.group(1), date_hint=date_hint, race_meta=race_meta)

        # meta-only fallback
        if meta.get("date") and meta.get("venue") and meta.get("race_no") is not None:
            venue_ja = str(meta["venue"])
            return RaceIdentity(
                date=str(meta["date"])[:10],
                venue_ja=venue_ja,
                race_no=int(meta["race_no"]),
                venue_en=_VENUE_JA_TO_EN.get(venue_ja),
                venue_code=_VENUE_JA_TO_CODE.get(venue_ja),
                source="meta",
                id_namespace="meta",
            )

        return None

    def _identity_from_catalog(
        self,
        hit: CatalogRace,
        *,
        raw: str,
        id_namespace: str,
    ) -> RaceIdentity:
        catalog_ref = CatalogRaceRef.parse(hit.catalog_id)
        numeric_ref = NumericRaceRef.parse(hit.numeric_race_id)
        core_ref = CoreRaceRef.parse(hit.core_race_id) or CoreRaceRef.from_catalog_row(
            date=hit.date,
            course=hit.course,
            race_no=hit.race_no,
            numeric_race_id=hit.numeric_race_id,
        )
        feature_ref = FeatureLookupRef.from_catalog(hit.feature_lookup_key or hit.catalog_id)
        public = raw.lower() if id_namespace == "slug" else None
        return RaceIdentity(
            date=hit.date,
            venue_ja=hit.course,
            race_no=hit.race_no,
            venue_code=hit.jra_venue_code or (core_ref.jra_venue_code if core_ref else None),
            venue_en=_VENUE_JA_TO_EN.get(hit.course),
            core_race_id=core_ref.as_id() if core_ref else None,
            catalog_race_id=hit.catalog_id,
            public_race_id=public,
            source="catalog",
            id_namespace=id_namespace,
            numeric_race_id=hit.numeric_race_id or None,
            feature_lookup_key=feature_ref.as_id(),
            catalog_ref=catalog_ref,
            numeric_ref=numeric_ref,
            core_ref=core_ref,
            feature_lookup_ref=feature_ref,
        )

    def _bridge_from_catalog(self, identity: RaceIdentity, raw: str) -> RaceIdentity:
        """Catalog 行があれば Core / FeatureLookup を numeric または course から埋める。"""
        if identity.id_namespace in ("catalog", "numeric") and identity.feature_lookup_key:
            return identity
        cat = self._catalog()
        hit = cat.lookup_any(raw)
        if hit is None and identity.numeric_race_id:
            hit = cat.lookup_numeric(identity.numeric_race_id)
        if hit is None and identity.date and identity.venue_ja and identity.race_no:
            hit = cat.lookup_date_course_race(
                identity.date, identity.venue_ja, identity.race_no
            )
        if hit is None:
            return identity
        ns = identity.id_namespace if identity.id_namespace not in ("unknown", "core", "") else "catalog"
        bridged = self._identity_from_catalog(hit, raw=raw, id_namespace=ns)
        if identity.id_namespace in ("slug", "venue_qualified", "ui_label"):
            bridged.id_namespace = identity.id_namespace
            bridged.source = identity.source
            if identity.public_race_id:
                bridged.public_race_id = identity.public_race_id
        return bridged

    def _hydrate(self, identity: RaceIdentity) -> RaceIdentity:
        if not identity.venue_en:
            identity.venue_en = _VENUE_JA_TO_EN.get(identity.venue_ja)
        if not identity.venue_code:
            identity.venue_code = _VENUE_JA_TO_CODE.get(identity.venue_ja)
        self._fill_derived_ids(identity)
        return identity

    def _fill_derived_ids(self, identity: RaceIdentity) -> None:
        if not identity.public_race_id:
            identity.public_race_id = self.to_public(identity)
        if not identity.catalog_race_id:
            identity.catalog_race_id = f"{identity.date}-{identity.venue_ja}-{identity.race_no}"
        if not identity.core_race_id and identity.core_ref:
            identity.core_race_id = identity.core_ref.as_id()
        if not identity.feature_lookup_key:
            if identity.catalog_ref:
                identity.feature_lookup_ref = FeatureLookupRef.from_catalog(
                    identity.catalog_ref.as_id()
                )
                identity.feature_lookup_key = identity.feature_lookup_ref.as_id()
            elif identity.core_race_id and identity.id_namespace == "core":
                identity.feature_lookup_ref = FeatureLookupRef.from_legacy_core(
                    identity.core_race_id
                )
                identity.feature_lookup_key = identity.feature_lookup_ref.as_id()
        if identity.feature_lookup_ref and not identity.feature_lookup_key:
            identity.feature_lookup_key = identity.feature_lookup_ref.as_id()
        if identity.core_ref and not identity.core_race_id:
            identity.core_race_id = identity.core_ref.as_id()
        if identity.numeric_ref and not identity.numeric_race_id:
            identity.numeric_race_id = identity.numeric_ref.as_id()

    def _lookup_db(self, identity: RaceIdentity) -> dict[str, Any] | None:
        candidates = [
            identity.core_race_id,
            identity.catalog_race_id,
            identity.public_race_id,
        ]
        for cid in candidates:
            if cid:
                row = self.repo.get(str(cid))
                if row:
                    return row
        rows = self.repo.list(
            date=identity.date,
            venue=identity.venue_ja,
            race_no=identity.race_no,
            limit=5,
        )
        return rows[0] if rows else None

    def _merge_db(self, identity: RaceIdentity, row: dict[str, Any]) -> RaceIdentity:
        identity.race_row = row
        identity.date = str(row.get("date") or identity.date)[:10]
        identity.venue_ja = str(row.get("venue") or identity.venue_ja)
        identity.race_no = int(row.get("race_no") or identity.race_no)
        identity.core_race_id = identity.core_race_id or row.get("core_race_id")
        identity.public_race_id = row.get("public_race_id") or identity.public_race_id
        if not identity.catalog_ref:
            identity.catalog_race_id = row.get("race_id") or identity.catalog_race_id
        identity.venue_code = identity.venue_code or row.get("venue_code")
        identity.venue_en = _VENUE_JA_TO_EN.get(identity.venue_ja) or identity.venue_en
        identity.source = "db"
        if not identity.feature_lookup_key and identity.id_namespace == "core":
            identity.feature_lookup_key = identity.core_race_id
            if identity.core_race_id:
                identity.feature_lookup_ref = FeatureLookupRef.from_legacy_core(
                    identity.core_race_id
                )
        return identity

    def _resolve_core_via_platform(self, identity: RaceIdentity) -> str | None:
        try:
            from ..engine.adapters import single_prediction_mapper as mapper

            probe = (
                identity.public_race_id
                or identity.catalog_race_id
                or identity.core_race_id
                or ""
            )
            return mapper._resolve_core_race_id_legacy(
                probe,
                race_meta=identity.as_meta(),
            )
        except Exception:
            return identity.core_race_id

    def _infer_date_hint(self, text: str) -> str | None:
        if "今日" in text or "本日" in text:
            return datetime.now(timezone.utc).date().isoformat()
        m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", text)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        m = re.search(r"(20\d{6})", text)
        if m:
            s = m.group(1)
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        # catalog 最新日
        rows = self.repo.list(limit=500)
        dates = sorted({str(r["date"]) for r in rows if r.get("date")})
        return dates[-1] if dates else date.today().isoformat()


_default_resolver: RaceResolver | None = None


def get_resolver() -> RaceResolver:
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = RaceResolver()
    return _default_resolver


def reset_resolver_for_tests() -> None:
    global _default_resolver
    _default_resolver = None


def resolve_identity(
    text_or_id: str,
    *,
    date_hint: str | None = None,
    race_meta: dict[str, Any] | None = None,
) -> RaceIdentity | None:
    return get_resolver().resolve(text_or_id, date_hint=date_hint, race_meta=race_meta)


def resolve_core_id(
    text_or_id: str,
    *,
    date_hint: str | None = None,
    race_meta: dict[str, Any] | None = None,
) -> str | None:
    return get_resolver().resolve_core_id(text_or_id, date_hint=date_hint, race_meta=race_meta)


def resolve_public_id(
    text_or_id: str,
    *,
    date_hint: str | None = None,
    race_meta: dict[str, Any] | None = None,
) -> str | None:
    return get_resolver().resolve_public_id(
        text_or_id, date_hint=date_hint, race_meta=race_meta
    )
