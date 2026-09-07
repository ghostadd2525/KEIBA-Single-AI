# -*- coding: utf-8 -*-
"""
Version16 Metadata Completion Research

Backfill unknown race metadata for Weakness Atlas reliability.
Research-only. Does NOT mutate Prediction / PE / CE / AI / Challenge /
Resolver / ResultAutomation.

Priority: existing DB → existing PI → Netkeiba → JRA
"""
from __future__ import annotations

import json
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .config import evidence_root, repo_root
from .prediction_corpus import _age_group, _is_young_horse
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-metadata-completion/1.0"

META_FIELDS = (
    "surface",
    "distance",
    "field_size",
    "age_group",
    "weather",
    "going",
    "race_class",
    "course_type",
)

_SURFACE_DIST_RE = re.compile(
    r"(芝|ダート|ダ|障害)\s*([0-9]{3,4})\s*m",
    re.I,
)
_WEATHER_RE = re.compile(r"天候\s*[:：]?\s*([^\s/<]+)")
_GOING_RE = re.compile(r"馬場\s*[:：]?\s*([^\s/<]+)")
_DIST_ONLY_RE = re.compile(r"([0-9]{3,4})\s*m")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _blank(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v.strip() in {"", "unknown", "None", "null", "?"}:
        return True
    if isinstance(v, (int, float)) and float(v) <= 0:
        return True
    return False


def _norm_surface(v: Any) -> str | None:
    if _blank(v):
        return None
    s = str(v).strip()
    sl = s.lower()
    if "芝" in s or sl == "turf":
        return "芝"
    if "ダ" in s or "dirt" in sl:
        return "ダート"
    if "障" in s:
        return "障害"
    return s


def _norm_distance(v: Any) -> int | None:
    if _blank(v):
        return None
    try:
        d = int(float(v))
    except (TypeError, ValueError):
        m = _DIST_ONLY_RE.search(str(v))
        if not m:
            return None
        d = int(m.group(1))
    return d if d > 0 else None


def _norm_field(v: Any) -> int | None:
    if _blank(v):
        return None
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _norm_going(v: Any) -> str | None:
    if _blank(v):
        return None
    g = str(v).strip()
    for tok in ("稍重", "不良", "重", "良"):
        if tok in g:
            return tok
    return g


def _norm_weather(v: Any) -> str | None:
    if _blank(v):
        return None
    return str(v).strip()


def _course_type_from_surface(surface: str | None) -> str | None:
    s = _norm_surface(surface)
    if not s:
        return None
    if s == "芝":
        return "turf"
    if s == "ダート":
        return "dirt"
    if s == "障害":
        return "obstacle"
    return None


def _course_type_from_pi(course: Any) -> str | None:
    if _blank(course):
        return None
    c = str(course).strip().lower()
    if "turf" in c or "芝" in c:
        return "turf"
    if "dirt" in c or "ダ" in c:
        return "dirt"
    # PI sometimes stores venue course code; keep raw lightly
    if c in {"turf", "dirt", "obstacle"}:
        return c
    return str(course).strip()


def parse_netkeiba_race_meta_html(html: str) -> dict[str, Any]:
    """Research-only HTML parse for race condition metadata."""
    out: dict[str, Any] = {}
    if not html:
        return out
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    m = _SURFACE_DIST_RE.search(html) or _SURFACE_DIST_RE.search(text)
    if m:
        out["surface"] = _norm_surface(m.group(1))
        out["distance"] = _norm_distance(m.group(2))

    wm = _WEATHER_RE.search(text)
    if wm:
        out["weather"] = _norm_weather(wm.group(1))
    gm = _GOING_RE.search(text)
    if gm:
        out["going"] = _norm_going(gm.group(1))

    # Diary_Snap_RaceData01 style
    snap = re.search(
        r"Diary_Snap_RaceData[^>]*>(.*?)</(?:div|span|p)>",
        html,
        re.I | re.S,
    )
    if snap:
        chunk = _strip_tags(snap.group(1))
        if "weather" not in out:
            wm2 = _WEATHER_RE.search(chunk)
            if wm2:
                out["weather"] = _norm_weather(wm2.group(1))
        if "going" not in out:
            gm2 = _GOING_RE.search(chunk)
            if gm2:
                out["going"] = _norm_going(gm2.group(1))
        if "distance" not in out or "surface" not in out:
            m2 = _SURFACE_DIST_RE.search(chunk)
            if m2:
                out.setdefault("surface", _norm_surface(m2.group(1)))
                out.setdefault("distance", _norm_distance(m2.group(2)))

    field_m = re.search(r"出走[^\d]*(\d+)\s*頭", text)
    if field_m:
        out["field_size"] = _norm_field(field_m.group(1))
    return {k: v for k, v in out.items() if not _blank(v)}


def _strip_tags(raw: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw or "")).strip()


def _merge_field(
    target: dict[str, Any],
    field: str,
    value: Any,
    *,
    source: str,
    chain: dict[str, str],
) -> bool:
    if field not in META_FIELDS and field not in {
        "class_label",
        "venue",
        "race_date",
        "numeric_race_id",
    }:
        return False
    if _blank(value):
        return False
    if field == "surface":
        value = _norm_surface(value)
    elif field == "distance":
        value = _norm_distance(value)
    elif field == "field_size":
        value = _norm_field(value)
    elif field == "going":
        value = _norm_going(value)
    elif field == "weather":
        value = _norm_weather(value)
    elif field == "course_type":
        value = str(value).strip() if value else None
    elif field == "age_group":
        value = str(value).strip() if value else None
    elif field == "race_class":
        value = str(value).strip() if value else None
    if _blank(value):
        return False
    if not _blank(target.get(field)):
        return False
    target[field] = value
    chain[field] = source
    return True


class MetadataCompletion:
    def __init__(self, *, enable_netkeiba: bool | None = None, netkeiba_limit: int | None = None) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()
        if enable_netkeiba is None:
            raw = (os.environ.get("RESEARCH_METADATA_NETKEIBA") or "1").strip().lower()
            enable_netkeiba = raw not in ("0", "false", "no", "off")
        self.enable_netkeiba = bool(enable_netkeiba)
        self.netkeiba_limit = int(
            netkeiba_limit
            if netkeiba_limit is not None
            else os.environ.get("RESEARCH_METADATA_NETKEIBA_LIMIT", "80")
        )

    def _baseline_index(self) -> dict[str, dict[str, Any]]:
        paths = [
            Path(__file__).resolve().parents[2]
            / "fixtures"
            / "stats"
            / "baseline-285r-evaluations.json",
            self.root / "fixtures" / "stats" / "baseline-285r-evaluations.json",
            self.root
            / "services"
            / "win5-ai"
            / "fixtures"
            / "stats"
            / "baseline-285r-evaluations.json",
        ]
        for p in paths:
            if not p.exists():
                continue
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            rows = payload.get("rows") or []
            return {str(r.get("race_id")): r for r in rows if r.get("race_id")}
        return {}

    def _pi_index(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        dirs = [
            self.root / "public" / "data" / "predictions",
            Path(__file__).resolve().parents[4] / "public" / "data" / "predictions",
        ]
        for d in dirs:
            if not d.is_dir():
                continue
            for path in d.glob("*.pi.json"):
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                rid = str(payload.get("race_id") or path.stem)
                if rid:
                    out[rid] = payload
        return out

    def _load_corpus_race_ids(self, conn) -> list[str]:
        rows = conn.execute(
            """
            SELECT DISTINCT race_id FROM research_prediction_corpus
            WHERE race_id NOT LIKE '2099%'
            ORDER BY race_id
            """
        ).fetchall()
        return [str(r["race_id"]) for r in rows]

    def _seed_row(self, race_id: str) -> dict[str, Any]:
        return {
            "race_id": race_id,
            "surface": None,
            "distance": None,
            "field_size": None,
            "age_group": None,
            "weather": None,
            "going": None,
            "race_class": None,
            "course_type": None,
            "class_label": None,
            "venue": None,
            "race_date": None,
            "numeric_race_id": None,
            "_chain": {},
        }

    def _apply_db_sources(self, conn, row: dict[str, Any]) -> None:
        race_id = row["race_id"]
        chain: dict[str, str] = row["_chain"]

        # 1) research corpus
        crow = conn.execute(
            """
            SELECT surface, distance, class_label, age_group, venue, race_date, meta_json, source
            FROM research_prediction_corpus
            WHERE race_id=?
            ORDER BY updated_at DESC LIMIT 1
            """,
            (race_id,),
        ).fetchone()
        if crow:
            src = "db.research_prediction_corpus"
            _merge_field(row, "surface", crow["surface"], source=src, chain=chain)
            _merge_field(row, "distance", crow["distance"], source=src, chain=chain)
            _merge_field(row, "race_class", crow["class_label"], source=src, chain=chain)
            _merge_field(row, "class_label", crow["class_label"], source=src, chain=chain)
            if crow["age_group"] and crow["age_group"] != "unknown":
                _merge_field(row, "age_group", crow["age_group"], source=src, chain=chain)
            _merge_field(row, "venue", crow["venue"], source=src, chain=chain)
            _merge_field(row, "race_date", crow["race_date"], source=src, chain=chain)
            try:
                meta = json.loads(crow["meta_json"] or "{}")
            except Exception:
                meta = {}
            _merge_field(
                row, "field_size", meta.get("field_size"), source=src + ".meta", chain=chain
            )
            _merge_field(
                row, "going", meta.get("going"), source=src + ".meta", chain=chain
            )
            _merge_field(
                row, "weather", meta.get("weather"), source=src + ".meta", chain=chain
            )

        # 2) race_results
        rr = conn.execute(
            """
            SELECT surface, distance, going, field_size, venue, race_date, result_json
            FROM race_results WHERE race_id=?
            """,
            (race_id,),
        ).fetchone()
        if rr:
            src = "db.race_results"
            _merge_field(row, "surface", rr["surface"], source=src, chain=chain)
            _merge_field(row, "distance", rr["distance"], source=src, chain=chain)
            _merge_field(row, "going", rr["going"], source=src, chain=chain)
            _merge_field(row, "field_size", rr["field_size"], source=src, chain=chain)
            _merge_field(row, "venue", rr["venue"], source=src, chain=chain)
            _merge_field(row, "race_date", rr["race_date"], source=src, chain=chain)
            try:
                payload = json.loads(rr["result_json"] or "{}")
            except Exception:
                payload = {}
            for k in ("weather", "天候", "tenko"):
                if payload.get(k):
                    _merge_field(row, "weather", payload.get(k), source=src + ".json", chain=chain)
            for k in ("going", "馬場", "baba"):
                if payload.get(k):
                    _merge_field(row, "going", payload.get(k), source=src + ".json", chain=chain)
            _merge_field(row, "surface", payload.get("surface"), source=src + ".json", chain=chain)
            _merge_field(row, "distance", payload.get("distance"), source=src + ".json", chain=chain)
            if payload.get("numeric_race_id"):
                _merge_field(
                    row,
                    "numeric_race_id",
                    str(payload.get("numeric_race_id")),
                    source=src + ".json",
                    chain=chain,
                )
            fo = payload.get("finish_order")
            if isinstance(fo, list) and fo:
                _merge_field(row, "field_size", len(fo), source=src + ".finish_order", chain=chain)

        # 3) races catalog
        race = conn.execute(
            """
            SELECT surface, distance, class_label, field_size, venue, date, grade, extra_json
            FROM races WHERE race_id=?
            """,
            (race_id,),
        ).fetchone()
        if not race and crow and crow["race_date"] and crow["venue"]:
            # soft join by date|venue|race_no if race_id encodes race_no
            m = re.search(r"-(\d{1,2})$", race_id)
            if m:
                race = conn.execute(
                    """
                    SELECT surface, distance, class_label, field_size, venue, date, grade, extra_json
                    FROM races WHERE date=? AND venue=? AND race_no=?
                    LIMIT 1
                    """,
                    (crow["race_date"], crow["venue"], int(m.group(1))),
                ).fetchone()
        if race:
            src = "db.races"
            _merge_field(row, "surface", race["surface"], source=src, chain=chain)
            _merge_field(row, "distance", race["distance"], source=src, chain=chain)
            _merge_field(row, "race_class", race["class_label"], source=src, chain=chain)
            _merge_field(row, "class_label", race["class_label"], source=src, chain=chain)
            _merge_field(row, "field_size", race["field_size"], source=src, chain=chain)
            _merge_field(row, "venue", race["venue"], source=src, chain=chain)
            _merge_field(row, "race_date", race["date"], source=src, chain=chain)
            try:
                extra = json.loads(race["extra_json"] or "{}")
            except Exception:
                extra = {}
            _merge_field(row, "going", extra.get("going"), source=src + ".extra", chain=chain)
            _merge_field(row, "weather", extra.get("weather"), source=src + ".extra", chain=chain)
            if extra.get("numeric_race_id"):
                _merge_field(
                    row,
                    "numeric_race_id",
                    str(extra.get("numeric_race_id")),
                    source=src + ".extra",
                    chain=chain,
                )

        # 4) race_evaluations.meta_json (baseline import)
        ev = conn.execute(
            """
            SELECT meta_json FROM race_evaluations
            WHERE race_id=?
            ORDER BY id DESC LIMIT 1
            """,
            (race_id,),
        ).fetchone()
        if ev:
            src = "db.race_evaluations"
            try:
                meta = json.loads(ev["meta_json"] or "{}")
            except Exception:
                meta = {}
            for f in ("surface", "distance", "going", "field_size", "weather"):
                _merge_field(row, f, meta.get(f), source=src, chain=chain)

        # 5) historical bundles
        hb = conn.execute(
            """
            SELECT surface, distance, class_label, runner_count, venue, race_date,
                   race_name, bundle_json, meta_json
            FROM research_historical_bundles
            WHERE race_id=?
            ORDER BY updated_at DESC LIMIT 1
            """,
            (race_id,),
        ).fetchone()
        if hb:
            src = "db.research_historical_bundles"
            _merge_field(row, "surface", hb["surface"], source=src, chain=chain)
            _merge_field(row, "distance", hb["distance"], source=src, chain=chain)
            label = hb["class_label"] or hb["race_name"]
            _merge_field(row, "race_class", label, source=src, chain=chain)
            _merge_field(row, "class_label", label, source=src, chain=chain)
            _merge_field(row, "field_size", hb["runner_count"], source=src, chain=chain)
            _merge_field(row, "venue", hb["venue"], source=src, chain=chain)
            _merge_field(row, "race_date", hb["race_date"], source=src, chain=chain)
            try:
                bundle = json.loads(hb["bundle_json"] or "{}")
            except Exception:
                bundle = {}
            info = bundle.get("race_info") or bundle.get("race") or {}
            if isinstance(info, dict):
                _merge_field(row, "surface", info.get("surface"), source=src + ".bundle", chain=chain)
                _merge_field(row, "distance", info.get("distance"), source=src + ".bundle", chain=chain)
                _merge_field(row, "going", info.get("going"), source=src + ".bundle", chain=chain)
                _merge_field(row, "weather", info.get("weather"), source=src + ".bundle", chain=chain)
                _merge_field(
                    row,
                    "field_size",
                    info.get("field_size") or info.get("head_count"),
                    source=src + ".bundle",
                    chain=chain,
                )
                if info.get("numeric_race_id"):
                    _merge_field(
                        row,
                        "numeric_race_id",
                        str(info.get("numeric_race_id")),
                        source=src + ".bundle",
                        chain=chain,
                    )
            runners = bundle.get("runners") or bundle.get("entries") or []
            if isinstance(runners, list) and runners:
                _merge_field(row, "field_size", len(runners), source=src + ".runners", chain=chain)

        # 6) evidence snapshot payload
        snap = conn.execute(
            """
            SELECT payload_json FROM research_prediction_snapshots
            WHERE race_id=?
            ORDER BY created_at DESC LIMIT 1
            """,
            (race_id,),
        ).fetchone()
        if snap:
            src = "db.research_prediction_snapshots"
            try:
                payload = json.loads(snap["payload_json"] or "{}")
            except Exception:
                payload = {}
            race_obj = payload.get("race") or payload.get("race_info") or {}
            if isinstance(race_obj, dict):
                for f in ("surface", "distance", "going", "weather", "field_size"):
                    _merge_field(row, f, race_obj.get(f), source=src, chain=chain)
                if race_obj.get("class_label") or race_obj.get("race_name"):
                    lab = race_obj.get("class_label") or race_obj.get("race_name")
                    _merge_field(row, "race_class", lab, source=src, chain=chain)
                    _merge_field(row, "class_label", lab, source=src, chain=chain)
            runners = payload.get("runners") or []
            if isinstance(runners, list) and runners:
                _merge_field(row, "field_size", len(runners), source=src + ".runners", chain=chain)

    def _apply_baseline(self, row: dict[str, Any], baseline: dict[str, dict[str, Any]]) -> None:
        b = baseline.get(row["race_id"])
        if not b:
            return
        src = "fixture.baseline_285r"
        chain = row["_chain"]
        for f in ("surface", "distance", "going", "field_size"):
            _merge_field(row, f, b.get(f), source=src, chain=chain)
        _merge_field(row, "venue", b.get("venue"), source=src, chain=chain)
        _merge_field(row, "race_date", b.get("race_date"), source=src, chain=chain)

    def _apply_pi(self, row: dict[str, Any], pi_index: dict[str, dict[str, Any]]) -> None:
        p = pi_index.get(row["race_id"])
        if not p:
            return
        src = "pi.json"
        chain = row["_chain"]
        _merge_field(row, "venue", p.get("venue") or p.get("course"), source=src, chain=chain)
        _merge_field(row, "race_date", p.get("race_date"), source=src, chain=chain)
        label = p.get("race_name") or p.get("race_label")
        _merge_field(row, "race_class", label, source=src, chain=chain)
        _merge_field(row, "class_label", label, source=src, chain=chain)
        ct = _course_type_from_pi(p.get("course"))
        # only accept turf/dirt-like values; venue names are not course_type
        if ct in {"turf", "dirt", "obstacle"}:
            _merge_field(row, "course_type", ct, source=src, chain=chain)
        pred = p.get("prediction") or {}
        cands = pred.get("candidates") or []
        if isinstance(cands, list) and cands:
            _merge_field(row, "field_size", len(cands), source=src + ".candidates", chain=chain)

    def _apply_netkeiba(self, row: dict[str, Any], client) -> dict[str, Any]:
        nid = row.get("numeric_race_id")
        if not nid:
            return {"skipped": "numeric_race_id_missing"}
        # only fetch if still missing critical fields
        need = any(_blank(row.get(f)) for f in ("surface", "distance", "going", "weather", "field_size"))
        if not need:
            return {"skipped": "already_complete"}
        url = f"https://race.netkeiba.com/race/result.html?race_id={nid}"
        try:
            html = client.fetch(url, label="race_meta")
        except Exception as exc:
            return {"error": str(exc)}
        parsed = parse_netkeiba_race_meta_html(html)
        chain = row["_chain"]
        filled = []
        for f, v in parsed.items():
            if _merge_field(row, f, v, source="netkeiba.result_html", chain=chain):
                filled.append(f)
        return {"filled": filled, "parsed": parsed}

    def _derive(self, row: dict[str, Any]) -> None:
        chain = row["_chain"]
        if _blank(row.get("course_type")):
            ct = _course_type_from_surface(row.get("surface"))
            _merge_field(row, "course_type", ct, source="derive.surface", chain=chain)
        if _blank(row.get("race_class")) and not _blank(row.get("class_label")):
            _merge_field(
                row, "race_class", row.get("class_label"), source="derive.class_label", chain=chain
            )
        if _blank(row.get("age_group")) or row.get("age_group") == "unknown":
            age = _age_group(row.get("class_label") or row.get("race_class"), row.get("race_class"))
            if age and age != "unknown":
                # force replace unknown
                if _blank(row.get("age_group")) or row.get("age_group") == "unknown":
                    row["age_group"] = age
                    chain["age_group"] = "derive.age_group"

    def measure_coverage(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(rows) or 1
        out: dict[str, Any] = {"n_races": len(rows), "fields": {}}
        for f in META_FIELDS:
            known = sum(1 for r in rows if not _blank(r.get(f)) and r.get(f) != "unknown")
            out["fields"][f] = {
                "known": known,
                "unknown": len(rows) - known,
                "coverage": round(known / n, 4),
            }
        out["mean_coverage"] = round(
            sum(out["fields"][f]["coverage"] for f in META_FIELDS) / len(META_FIELDS), 4
        )
        return out

    def _snapshot_before_from_db(self, conn, race_ids: list[str]) -> list[dict[str, Any]]:
        """Pre-completion view: corpus + race_results only (no baseline/netkeiba merge)."""
        rows = []
        for rid in race_ids:
            row = self._seed_row(rid)
            # corpus
            crow = conn.execute(
                """
                SELECT surface, distance, class_label, age_group, meta_json
                FROM research_prediction_corpus WHERE race_id=?
                ORDER BY updated_at DESC LIMIT 1
                """,
                (rid,),
            ).fetchone()
            if crow:
                row["surface"] = _norm_surface(crow["surface"])
                row["distance"] = _norm_distance(crow["distance"])
                row["race_class"] = crow["class_label"]
                row["class_label"] = crow["class_label"]
                if crow["age_group"] and crow["age_group"] != "unknown":
                    row["age_group"] = crow["age_group"]
                try:
                    meta = json.loads(crow["meta_json"] or "{}")
                except Exception:
                    meta = {}
                row["field_size"] = _norm_field(meta.get("field_size"))
                row["going"] = _norm_going(meta.get("going"))
                row["weather"] = _norm_weather(meta.get("weather"))
            rr = conn.execute(
                """
                SELECT surface, distance, going, field_size, result_json
                FROM race_results WHERE race_id=?
                """,
                (rid,),
            ).fetchone()
            if rr:
                row["surface"] = row["surface"] or _norm_surface(rr["surface"])
                row["distance"] = row["distance"] or _norm_distance(rr["distance"])
                row["going"] = row["going"] or _norm_going(rr["going"])
                row["field_size"] = row["field_size"] or _norm_field(rr["field_size"])
                try:
                    payload = json.loads(rr["result_json"] or "{}")
                except Exception:
                    payload = {}
                row["weather"] = row["weather"] or _norm_weather(
                    payload.get("weather") or payload.get("天候")
                )
                row["going"] = row["going"] or _norm_going(
                    payload.get("going") or payload.get("馬場")
                )
                row["surface"] = row["surface"] or _norm_surface(payload.get("surface"))
                row["distance"] = row["distance"] or _norm_distance(payload.get("distance"))
                fo = payload.get("finish_order")
                if isinstance(fo, list) and fo and _blank(row.get("field_size")):
                    row["field_size"] = len(fo)
            row["course_type"] = _course_type_from_surface(row.get("surface"))
            if _blank(row.get("age_group")):
                age = _age_group(row.get("class_label"), row.get("race_class"))
                row["age_group"] = age if age != "unknown" else None
            rows.append(row)
        return rows

    def complete(self) -> dict[str, Any]:
        run_id = f"meta-{uuid.uuid4().hex[:12]}"
        started = _now()
        conn = connect()
        baseline = self._baseline_index()
        pi_index = self._pi_index()
        netkeiba_stats: dict[str, Any] = {
            "enabled": self.enable_netkeiba,
            "attempted": 0,
            "filled": 0,
            "errors": 0,
            "skipped": 0,
            "jra_status": "unavailable_no_local_provider",
        }
        try:
            race_ids = self._load_corpus_race_ids(conn)
            before_rows = self._snapshot_before_from_db(conn, race_ids)
            coverage_before = self.measure_coverage(before_rows)

            client = None
            if self.enable_netkeiba:
                from .collector.netkeiba_client import ResearchNetkeibaClient

                client = ResearchNetkeibaClient()

            completed: list[dict[str, Any]] = []
            source_counter: Counter[str] = Counter()
            for rid in race_ids:
                row = self._seed_row(rid)
                self._apply_db_sources(conn, row)
                self._apply_baseline(row, baseline)
                self._apply_pi(row, pi_index)
                self._derive(row)

                # Netkeiba last among remote (before JRA which is unavailable)
                if client and netkeiba_stats["attempted"] < self.netkeiba_limit:
                    need = any(
                        _blank(row.get(f)) for f in ("surface", "distance", "going", "weather")
                    )
                    if need and row.get("numeric_race_id"):
                        netkeiba_stats["attempted"] += 1
                        res = self._apply_netkeiba(row, client)
                        if res.get("filled"):
                            netkeiba_stats["filled"] += 1
                        elif res.get("error"):
                            netkeiba_stats["errors"] += 1
                        else:
                            netkeiba_stats["skipped"] += 1
                        self._derive(row)

                for src in row["_chain"].values():
                    source_counter[src] += 1

                filled_n = sum(
                    1
                    for f in META_FIELDS
                    if not _blank(row.get(f)) and row.get(f) != "unknown"
                )
                completeness = round(filled_n / len(META_FIELDS), 4)
                now = _now()
                conn.execute(
                    """
                    INSERT INTO research_race_meta(
                      race_id, surface, distance, field_size, age_group, weather, going,
                      race_class, course_type, class_label, venue, race_date, numeric_race_id,
                      source_chain_json, completeness, meta_json, created_at, updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(race_id) DO UPDATE SET
                      surface=excluded.surface,
                      distance=excluded.distance,
                      field_size=excluded.field_size,
                      age_group=excluded.age_group,
                      weather=excluded.weather,
                      going=excluded.going,
                      race_class=excluded.race_class,
                      course_type=excluded.course_type,
                      class_label=excluded.class_label,
                      venue=excluded.venue,
                      race_date=excluded.race_date,
                      numeric_race_id=excluded.numeric_race_id,
                      source_chain_json=excluded.source_chain_json,
                      completeness=excluded.completeness,
                      meta_json=excluded.meta_json,
                      updated_at=excluded.updated_at
                    """,
                    (
                        rid,
                        row.get("surface"),
                        row.get("distance"),
                        row.get("field_size"),
                        row.get("age_group"),
                        row.get("weather"),
                        row.get("going"),
                        row.get("race_class"),
                        row.get("course_type"),
                        row.get("class_label"),
                        row.get("venue"),
                        row.get("race_date"),
                        row.get("numeric_race_id"),
                        json.dumps(row["_chain"], ensure_ascii=False),
                        completeness,
                        json.dumps(
                            {"source_counts_local": dict(Counter(row["_chain"].values()))},
                            ensure_ascii=False,
                        ),
                        now,
                        now,
                    ),
                )

                # Patch research corpus columns only (never predictions)
                age = row.get("age_group") or "unknown"
                young = 1 if _is_young_horse(str(age)) else 0
                conn.execute(
                    """
                    UPDATE research_prediction_corpus
                    SET surface=COALESCE(?, surface),
                        distance=COALESCE(?, distance),
                        class_label=COALESCE(?, class_label),
                        age_group=CASE
                          WHEN ? != 'unknown' THEN ?
                          ELSE age_group
                        END,
                        is_young_horse=CASE
                          WHEN ? != 'unknown' THEN ?
                          ELSE is_young_horse
                        END,
                        updated_at=?
                    WHERE race_id=?
                    """,
                    (
                        row.get("surface"),
                        row.get("distance"),
                        row.get("class_label") or row.get("race_class"),
                        age,
                        age,
                        age,
                        young,
                        now,
                        rid,
                    ),
                )
                # enrich meta_json with completed fields
                crow = conn.execute(
                    "SELECT meta_json FROM research_prediction_corpus WHERE race_id=? LIMIT 1",
                    (rid,),
                ).fetchone()
                if crow:
                    try:
                        meta = json.loads(crow["meta_json"] or "{}")
                    except Exception:
                        meta = {}
                    meta["v16_meta"] = {
                        "field_size": row.get("field_size"),
                        "going": row.get("going"),
                        "weather": row.get("weather"),
                        "course_type": row.get("course_type"),
                        "race_class": row.get("race_class"),
                        "source_chain": row["_chain"],
                    }
                    conn.execute(
                        "UPDATE research_prediction_corpus SET meta_json=?, updated_at=? WHERE race_id=?",
                        (json.dumps(meta, ensure_ascii=False), now, rid),
                    )

                completed.append(row)

            conn.commit()
            coverage_after = self.measure_coverage(completed)
            improvement = {}
            for f in META_FIELDS:
                b = coverage_before["fields"][f]["coverage"]
                a = coverage_after["fields"][f]["coverage"]
                improvement[f] = {
                    "before": b,
                    "after": a,
                    "delta_pp": round((a - b) * 100, 2),
                    "known_before": coverage_before["fields"][f]["known"],
                    "known_after": coverage_after["fields"][f]["known"],
                }

            finished = _now()
            summary = {
                "n_races": len(race_ids),
                "baseline_rows": len(baseline),
                "pi_rows": len(pi_index),
                "source_fills": dict(source_counter.most_common(30)),
                "netkeiba": netkeiba_stats,
                "mean_coverage_before": coverage_before["mean_coverage"],
                "mean_coverage_after": coverage_after["mean_coverage"],
            }
            conn.execute(
                """
                INSERT INTO research_metadata_runs(
                  run_id, schema_version, started_at, finished_at, status,
                  coverage_before_json, coverage_after_json, summary_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    run_id,
                    SCHEMA_VERSION,
                    started,
                    finished,
                    "ok",
                    json.dumps(coverage_before, ensure_ascii=False),
                    json.dumps(coverage_after, ensure_ascii=False),
                    json.dumps(summary, ensure_ascii=False),
                    finished,
                ),
            )
            conn.commit()
            return {
                "run_id": run_id,
                "schema_version": SCHEMA_VERSION,
                "generated_at": finished,
                "coverage_before": coverage_before,
                "coverage_after": coverage_after,
                "improvement": improvement,
                "summary": summary,
                "prediction_mutation": "FORBIDDEN",
            }
        finally:
            conn.close()


def _unknown_share(report: dict[str, Any], axis: str) -> dict[str, Any]:
    rows = (report.get("by_axis") or {}).get(axis) or []
    total = sum(int(r.get("n") or 0) for r in rows) or 1
    unk = next((r for r in rows if r.get("segment") == "unknown"), None)
    n_unk = int(unk.get("n") or 0) if unk else 0
    return {
        "n_unknown": n_unk,
        "share": round(n_unk / total, 4),
        "weakness_index": unk.get("weakness_index") if unk else None,
    }


def compute_weakness_delta(v15: dict[str, Any], v16: dict[str, Any]) -> dict[str, Any]:
    axes = sorted(set((v15.get("by_axis") or {}) | (v16.get("by_axis") or {})))
    axis_delta = {}
    for axis in axes:
        b = _unknown_share(v15, axis)
        a = _unknown_share(v16, axis)
        axis_delta[axis] = {
            "unknown_before": b["n_unknown"],
            "unknown_after": a["n_unknown"],
            "unknown_delta": a["n_unknown"] - b["n_unknown"],
            "share_before": b["share"],
            "share_after": a["share"],
            "share_delta_pp": round((a["share"] - b["share"]) * 100, 2),
        }
    s15 = v15.get("sample") or {}
    s16 = v16.get("sample") or {}
    return {
        "sample_before": s15,
        "sample_after": s16,
        "axis_unknown_delta": axis_delta,
        "priority_before_top5": (v15.get("priority_map") or [])[:5],
        "priority_after_top5": (v16.get("priority_map") or [])[:5],
    }


def write_completion_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    imp = report.get("improvement") or {}
    lines = [
        "# Version16 Research - Metadata Completion",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"**Run:** `{report.get('run_id')}`  ",
        "**Scope:** Research only / Unknown reduction only / Prediction FORBIDDEN  ",
        "",
        "## Priority Chain",
        "",
        "1. Existing DB (`races`, `race_results`, `race_evaluations`, corpus, historical, snapshots)",
        "2. Existing PI (`*.pi.json`)",
        "3. Baseline fixture (`baseline-285r-evaluations.json` — treated as DB-adjacent offline)",
        "4. Netkeiba result HTML (research client; only when `numeric_race_id` present)",
        "5. JRA — unavailable (no local research provider)",
        "",
        "## Coverage Before → After",
        "",
        "| Feature | Known Before | Known After | Coverage Before | Coverage After | Δpp |",
        "|---------|-------------:|------------:|----------------:|---------------:|----:|",
    ]
    for f in META_FIELDS:
        x = imp.get(f) or {}
        lines.append(
            f"| `{f}` | {x.get('known_before')} | {x.get('known_after')} | "
            f"{_pct(x.get('before'))} | {_pct(x.get('after'))} | {x.get('delta_pp')} |"
        )
    sm = report.get("summary") or {}
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Races: `{sm.get('n_races')}`",
            f"- Mean coverage: `{_pct(sm.get('mean_coverage_before'))}` → `{_pct(sm.get('mean_coverage_after'))}`",
            f"- Baseline fixture rows: `{sm.get('baseline_rows')}`",
            f"- PI files: `{sm.get('pi_rows')}`",
            f"- Netkeiba: `{json.dumps(sm.get('netkeiba') or {}, ensure_ascii=False)}`",
            f"- JRA: `unavailable_no_local_provider`",
            "",
            "## Guardrails",
            "",
            "- Did not mutate Prediction / PE / CE / AI / Challenge / Resolver / ResultAutomation",
            "- Wrote `research_race_meta` + patched `research_prediction_corpus` columns only",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_coverage_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    imp = report.get("improvement") or {}
    lines = [
        "# Version16 Research - Coverage Improvement",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "## Per-feature improvement",
        "",
    ]
    for f in META_FIELDS:
        x = imp.get(f) or {}
        lines.extend(
            [
                f"### `{f}`",
                "",
                f"- Before: `{x.get('known_before')}` known (`{_pct(x.get('before'))}`)",
                f"- After: `{x.get('known_after')}` known (`{_pct(x.get('after'))}`)",
                f"- Delta: `{x.get('delta_pp')} pp`",
                "",
            ]
        )
    src = (report.get("summary") or {}).get("source_fills") or {}
    lines.extend(
        [
            "## Source fill counts (field assignments)",
            "",
            "| Source | Assignments |",
            "|--------|------------:|",
        ]
    )
    for k, v in list(src.items())[:25]:
        lines.append(f"| `{k}` | {v} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_delta_md(delta: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version16 Research - Weakness Atlas Delta (vs V15)",
        "",
        "**Scope:** Re-generated Weakness Atlas after metadata completion.  ",
        "",
        "## Sample",
        "",
        f"- Before (V15): `{json.dumps(delta.get('sample_before') or {}, ensure_ascii=False)}`",
        f"- After (V16): `{json.dumps(delta.get('sample_after') or {}, ensure_ascii=False)}`",
        "",
        "## Unknown mass by axis",
        "",
        "| Axis | Unknown Before | Unknown After | Δ | Share Before | Share After | Δpp |",
        "|------|---------------:|--------------:|--:|-------------:|------------:|----:|",
    ]
    for axis, d in (delta.get("axis_unknown_delta") or {}).items():
        lines.append(
            f"| `{axis}` | {d.get('unknown_before')} | {d.get('unknown_after')} | "
            f"{d.get('unknown_delta')} | {_pct(d.get('share_before'))} | "
            f"{_pct(d.get('share_after'))} | {d.get('share_delta_pp')} |"
        )
    lines.extend(
        [
            "",
            "## Priority Map Top5 Before",
            "",
        ]
    )
    for r in delta.get("priority_before_top5") or []:
        lines.append(
            f"- `{r.get('axis')}={r.get('segment')}` WI={r.get('weakness_index')} "
            f"P={r.get('priority_score')} Strict={_pct(r.get('strict_rate'))}"
        )
    lines.extend(["", "## Priority Map Top5 After", ""])
    for r in delta.get("priority_after_top5") or []:
        lines.append(
            f"- `{r.get('axis')}={r.get('segment')}` WI={r.get('weakness_index')} "
            f"P={r.get('priority_score')} Strict={_pct(r.get('strict_rate'))}"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "```",
            "Action Type: Metadata Completion (Research)",
            "Prediction Mutation: FORBIDDEN",
            "Implementation of product fixes: FORBIDDEN",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    from .weakness_atlas import WeaknessAtlas, write_atlas_md

    completer = MetadataCompletion()
    report = completer.complete()

    # Load V15 snapshot for delta
    v15_path = evidence_root() / "reports" / "v15-weakness-atlas.json"
    v15 = {}
    if v15_path.exists():
        try:
            v15 = json.loads(v15_path.read_text(encoding="utf-8"))
        except Exception:
            v15 = {}

    atlas = WeaknessAtlas().analyze()
    # Persist regenerated atlas as v16 + overwrite live weakness paths used by research
    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    v16_atlas_json = evidence_root() / "reports" / "v16-weakness-atlas.json"
    v16_atlas_json.parent.mkdir(parents=True, exist_ok=True)
    v16_atlas_json.write_text(
        json.dumps(atlas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Also refresh v15-style live file for continuity (research report)
    (evidence_root() / "reports" / "v15-weakness-atlas-post-v16.json").write_text(
        json.dumps(atlas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_atlas_md(atlas, docs / "v16-weakness-atlas-regenerated.md")

    delta = compute_weakness_delta(v15, atlas) if v15 else {"note": "v15 snapshot missing"}
    report["weakness_delta"] = delta
    report["atlas_sample"] = atlas.get("sample")

    write_completion_md(report, docs / "v16-metadata-completion.md")
    write_coverage_md(report, docs / "v16-coverage-improvement.md")
    write_delta_md(delta if isinstance(delta, dict) else {}, docs / "v16-weakness-delta.md")

    json_path = evidence_root() / "reports" / "v16-metadata-completion.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    out = dict(report)
    json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "completion": str(docs / "v16-metadata-completion.md"),
        "coverage": str(docs / "v16-coverage-improvement.md"),
        "delta": str(docs / "v16-weakness-delta.md"),
        "json": str(json_path),
        "atlas_json": str(v16_atlas_json),
    }
    return report
