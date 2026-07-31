# -*- coding: utf-8 -*-
"""Production race refresh — published race diff → entries → history → features."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import pandas as pd

from .features import build_features
from .horse_number_integrity import (
    REASON_HORSE_NUMBER_NOT_READY,
    REASON_INCOMPLETE,
    purge_feature_race_ids,
    validate_runners_horse_number_integrity,
    write_integrity_report,
)
from .netkeiba.client import NetkeibaClient, NetkeibaFetchError
from .netkeiba.horse_history import OUT_COLUMNS as HISTORY_COLUMNS, build_history_rows, fetch_horse_history
from .netkeiba.parse import (
    parse_entries_from_shutuba,
    parse_list_races_from_race_list,
    parse_meetings_from_race_list,
    parse_race_meta_from_shutuba,
    shutuba_has_race,
)
from .race_catalog import assign_venue_label_nos, make_win5_race_id
from .service import _resolve_ai_platform_root, _resolve_prediction_data_root


JST = ZoneInfo("Asia/Tokyo")
DAILY_FEATURES_NAME = "demo_runners_pace_market_features.csv"


@dataclass
class RefreshConfig:
    data_root: Path
    state_root: Path
    min_interval_sec: float = 1.0
    window_start_hour: int = 8
    window_end_hour: int = 20
    tz: ZoneInfo = JST
    # When set, features are written under this data root (demo_daily_outputs/...)
    # while merge baseline is still read from data_root.
    features_shadow_dir: Path | None = None

    @classmethod
    def from_env(cls) -> RefreshConfig:
        data_root = _resolve_prediction_data_root() or Path("/opt/expect-ai/platform/data")
        state_raw = (os.environ.get("PI_RACE_REFRESH_STATE_ROOT") or "").strip()
        state_root = Path(state_raw) if state_raw else data_root / "var" / "race_refresh"
        min_interval = float(os.environ.get("PI_NETKEIBA_MIN_INTERVAL_SEC", "1.0"))
        start_h = int(os.environ.get("PI_RACE_REFRESH_START_HOUR", "8"))
        end_h = int(os.environ.get("PI_RACE_REFRESH_END_HOUR", "20"))
        shadow_raw = (os.environ.get("PI_FEATURES_SHADOW_DIR") or "").strip()
        shadow_dir = Path(shadow_raw) if shadow_raw else None
        return cls(
            data_root=data_root,
            state_root=state_root,
            min_interval_sec=min_interval,
            window_start_hour=start_h,
            window_end_hour=end_h,
            features_shadow_dir=shadow_dir,
        )


@dataclass
class RaceSnapshotEntry:
    race_id: str
    numeric_race_id: str
    course: str
    race_number: int
    fingerprint: str
    features_ok: bool = False
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RefreshReport:
    date: str
    started_at: str
    finished_at: str = ""
    in_window: bool = True
    meeting_count: int = 0
    listed_count: int = 0
    published_count: int = 0
    skipped_unpublished: int = 0
    skipped_unchanged: int = 0
    updated_count: int = 0
    features_generated: int = 0
    features_skipped_horse_number: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)
    processed_race_ids: list[str] = field(default_factory=list)
    feature_ready_race_ids: list[str] = field(default_factory=list)
    feature_blocked_race_ids: list[str] = field(default_factory=list)
    daily_features_path: str = ""
    horse_number_integrity_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def log_lines(self) -> list[str]:
        return [
            f"[race-refresh] date={self.date}",
            f"[race-refresh] meetings={self.meeting_count} listed={self.listed_count} published={self.published_count}",
            f"[race-refresh] updated={self.updated_count} features_generated={self.features_generated}",
            f"[race-refresh] features_skipped_horse_number={self.features_skipped_horse_number}",
            f"[race-refresh] skipped_unpublished={self.skipped_unpublished} skipped_unchanged={self.skipped_unchanged}",
            f"[race-refresh] errors={self.error_count}",
        ]


def now_jst() -> datetime:
    return datetime.now(JST)


def in_refresh_window(now: datetime, *, start_hour: int, end_hour: int) -> bool:
    return start_hour <= now.hour < end_hour


def _fingerprint_sort_key(entry: dict[str, Any]) -> tuple[int, int, str]:
    hn = entry.get("horse_number")
    if hn is not None and str(hn) != "":
        try:
            return (0, int(hn), str(entry.get("horse_id") or ""))
        except (TypeError, ValueError):
            pass
    display = entry.get("display_order")
    try:
        display_i = int(display) if display is not None and str(display) != "" else 10_000
    except (TypeError, ValueError):
        display_i = 10_000
    return (1, display_i, str(entry.get("horse_id") or ""))


def compute_entries_fingerprint(entries: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for row in sorted(entries, key=_fingerprint_sort_key):
        parts.append(
            "|".join(
                [
                    str(row.get("horse_id") or ""),
                    str(row.get("horse_number") or ""),
                    str(row.get("_odds") or ""),
                    str(row.get("_popularity") or ""),
                    str(row.get("jockey") or ""),
                    str(row.get("weight") or ""),
                ]
            )
        )
    payload = f"{len(entries)}:" + ";".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _day_dir(config: RefreshConfig, date: str) -> Path:
    return config.state_root / date


def _snapshot_path(config: RefreshConfig, date: str) -> Path:
    return _day_dir(config, date) / "snapshot.json"


def _runners_path(config: RefreshConfig, date: str) -> Path:
    return _day_dir(config, date) / "runners.csv"


def _history_path(config: RefreshConfig, date: str) -> Path:
    return _day_dir(config, date) / "horse_history_raw.csv"


def daily_features_path(config: RefreshConfig, date: str) -> Path:
    return config.data_root / "demo_daily_outputs" / date / DAILY_FEATURES_NAME


def load_snapshot(config: RefreshConfig, date: str) -> dict[str, RaceSnapshotEntry]:
    path = _snapshot_path(config, date)
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, RaceSnapshotEntry] = {}
    for race_id, item in raw.get("races", {}).items():
        out[race_id] = RaceSnapshotEntry(**item)
    return out


def save_snapshot(config: RefreshConfig, date: str, snapshot: dict[str, RaceSnapshotEntry]) -> None:
    path = _snapshot_path(config, date)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "date": date,
        "updated_at": now_jst().isoformat(),
        "races": {rid: entry.to_dict() for rid, entry in snapshot.items()},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def discover_published_races(
    client: NetkeibaClient,
    date: str,
) -> tuple[list[Any], list[dict[str, Any]], int]:
    """
    Returns (meetings, published_race_refs, skipped_unpublished_count).
    published_race_refs items: race_id, numeric_race_id, course, race_number, race_name
    """
    list_html = client.fetch_race_list(date)
    meetings = parse_meetings_from_race_list(list_html)
    listed = parse_list_races_from_race_list(list_html)

    venues_present = sorted({m.venue for m in meetings} | {r.venue for r in listed})
    meeting_order = [m.venue for m in meetings]
    venue_labels = assign_venue_label_nos(venues_present, preferred_order=meeting_order)

    published: list[dict[str, Any]] = []
    skipped = 0

    for race in sorted(listed, key=lambda r: (r.venue, r.race_no)):
        try:
            html = client.fetch_shutuba(race.race_id)
        except NetkeibaFetchError:
            skipped += 1
            continue
        if not shutuba_has_race(html):
            skipped += 1
            continue
        entries = parse_entries_from_shutuba(html)
        if not entries:
            skipped += 1
            continue
        win5_id = make_win5_race_id(date, race.venue, race.race_no, venue_labels)
        published.append(
            {
                "race_id": win5_id,
                "numeric_race_id": race.race_id,
                "course": race.venue,
                "race_number": race.race_no,
                "race_name": getattr(race, "race_name", "") or "",
                "entries": entries,
                "shutuba_html": html,
            }
        )

    return meetings, published, skipped


def select_races_for_update(
    published: list[dict[str, Any]],
    snapshot: dict[str, RaceSnapshotEntry],
) -> tuple[list[dict[str, Any]], int]:
    to_update: list[dict[str, Any]] = []
    unchanged = 0
    for race in published:
        fp = compute_entries_fingerprint(race["entries"])
        prev = snapshot.get(race["race_id"])
        if prev and prev.fingerprint == fp and prev.features_ok:
            unchanged += 1
            continue
        race["fingerprint"] = fp
        to_update.append(race)
    return to_update, unchanged


def _runners_from_entries(
    race: dict[str, Any],
    date: str,
    meta: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in race["entries"]:
        hid = str(entry.get("horse_id") or "").strip()
        rows.append(
            {
                "race_id": race["race_id"],
                "numeric_race_id": race["numeric_race_id"],
                "date": date,
                "course": race["course"],
                "race_number": race["race_number"],
                "race_name": meta.get("race_name", race.get("race_name", "")),
                "target_surface": meta.get("surface", ""),
                "target_distance": meta.get("distance"),
                "turn": meta.get("turn", "unknown"),
                "weather": meta.get("weather", "unknown"),
                "track_condition": meta.get("track_condition", "unknown"),
                "frame_number": entry.get("frame", 0),
                "horse_number": entry.get("horse_number"),
                "horse_number_source": entry.get("horse_number_source"),
                "display_order": entry.get("display_order"),
                "horse_name": entry.get("horse_name", ""),
                "horse_url": entry.get("_horse_url", f"https://db.netkeiba.com/horse/{hid}/"),
                "horse_id": hid,
                "sex": entry.get("_sex", ""),
                "age": entry.get("_age"),
                "weight_carried": entry.get("weight", 0.0),
                "jockey": entry.get("jockey", ""),
                "odds": entry.get("_odds"),
                "popularity": entry.get("_popularity"),
            }
        )
    return rows


def process_race_pipeline(
    client: NetkeibaClient,
    race: dict[str, Any],
    date: str,
    *,
    fetch_history: bool | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """
    Build runners (+ optional horse history).

    Version7.4: 土日は DYNAMIC（runners/odds）のみ。近走は平日 STATIC CSV を保持。
    """
    from .history_store import is_weekend_jst

    html = race["shutuba_html"]
    meta = parse_race_meta_from_shutuba(
        html,
        date=date,
        venue=race["course"],
        race_no=race["race_number"],
        numeric_race_id=race["numeric_race_id"],
    )
    runners = _runners_from_entries(race, date, meta)
    history_rows: list[dict[str, Any]] = []
    do_history = fetch_history if fetch_history is not None else (not is_weekend_jst(date))
    if not do_history:
        print(
            f"[pi-keibanet] race_refresh skip history (STATIC hold) "
            f"race_id={race.get('race_id')} date={date}"
        )
        return runners, history_rows, meta

    for row in runners:
        hid = str(row.get("horse_id") or "").strip()
        if not hid:
            continue
        try:
            parsed = fetch_horse_history(client, hid)
        except NetkeibaFetchError:
            # Shutuba umaban/frame must still be persisted; history is best-effort.
            continue
        if not parsed:
            continue
        history_rows.extend(build_history_rows(row, parsed))
    return runners, history_rows, meta


def _load_csv(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if path.is_file():
        return pd.read_csv(path, encoding="utf-8-sig")
    if columns:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame()


def merge_day_frames(
    config: RefreshConfig,
    date: str,
    race_ids_to_replace: set[str],
    new_runners: list[dict[str, Any]],
    new_history: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    runners_path = _runners_path(config, date)
    history_path = _history_path(config, date)

    runners_df = _load_csv(runners_path)
    history_df = _load_csv(history_path, columns=list(HISTORY_COLUMNS))

    if not runners_df.empty and "race_id" in runners_df.columns and race_ids_to_replace:
        runners_df = runners_df[~runners_df["race_id"].astype(str).isin(race_ids_to_replace)]
    # Only drop prior history for races that actually produced new history rows.
    # Keeps last-known history when db.netkeiba history fetch fails.
    history_replace: set[str] = set()
    if new_history:
        history_replace = {
            str(r.get("race_id") or "").strip()
            for r in new_history
            if str(r.get("race_id") or "").strip()
        }
    if not history_df.empty and "race_id" in history_df.columns and history_replace:
        history_df = history_df[~history_df["race_id"].astype(str).isin(history_replace)]

    if new_runners:
        runners_df = pd.concat([runners_df, pd.DataFrame(new_runners)], ignore_index=True)
    if new_history:
        history_df = pd.concat([history_df, pd.DataFrame(new_history)], ignore_index=True)

    if not runners_df.empty:
        runners_df = runners_df.drop_duplicates(subset=["race_id", "horse_id"], keep="last")
    return runners_df, history_df


def features_output_path(config: RefreshConfig, date: str) -> Path:
    """Write target for daily features (shadow root when configured)."""
    root = config.features_shadow_dir or config.data_root
    return root / "demo_daily_outputs" / date / DAILY_FEATURES_NAME


def merge_daily_features(
    existing: pd.DataFrame | None,
    new_features: pd.DataFrame,
    updated_race_ids: set[str] | None,
) -> pd.DataFrame:
    """Replace only updated race_id rows; keep other races from existing CSV."""
    if updated_race_ids is None or existing is None or existing.empty:
        return new_features.copy()
    if "race_id" not in new_features.columns:
        return new_features.copy()
    if "race_id" not in existing.columns:
        return new_features.copy()

    updated = {str(x) for x in updated_race_ids}
    if not updated:
        return new_features.copy()

    keep = existing[~existing["race_id"].astype(str).isin(updated)].copy()
    fresh = new_features[new_features["race_id"].astype(str).isin(updated)].copy()
    if keep.empty:
        return fresh.reset_index(drop=True)
    if fresh.empty:
        return keep.reset_index(drop=True)
    return pd.concat([keep, fresh], ignore_index=True)


def invalidate_daily_feature_races(
    config: RefreshConfig,
    date: str,
    race_ids: set[str],
) -> Path:
    """Remove Feature CSV rows for races that failed horse_number integrity."""
    out_path = features_output_path(config, date)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path = daily_features_path(config, date)
    source = out_path if out_path.is_file() else baseline_path
    if source.is_file():
        existing = pd.read_csv(source, encoding="utf-8-sig", low_memory=False)
        merged = purge_feature_race_ids(existing, set(race_ids or set()))
    else:
        merged = pd.DataFrame(columns=["race_id", "horse_id", "horse_number", "horse_name"])
    merged.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def write_daily_features(
    config: RefreshConfig,
    date: str,
    runners_df: pd.DataFrame,
    history_df: pd.DataFrame,
    *,
    updated_race_ids: set[str] | None = None,
    invalidate_race_ids: set[str] | None = None,
    require_horse_number_integrity: bool = True,
) -> Path:
    """Build/merge daily features. Formal horse_number required when integrity gate is on."""
    work = runners_df.copy() if runners_df is not None else pd.DataFrame()
    target_ids = {str(x) for x in (updated_race_ids or [])} if updated_race_ids is not None else None
    blocked: set[str] = set()

    if require_horse_number_integrity and not work.empty:
        integrity = validate_runners_horse_number_integrity(
            work,
            date=date,
            race_ids=target_ids,
        )
        blocked = set(integrity.blocked_race_ids)
        if blocked:
            if "race_id" in work.columns:
                work = work[~work["race_id"].astype(str).isin(blocked)].copy()
            if target_ids is not None:
                target_ids = {rid for rid in target_ids if rid not in blocked}
            invalidate_race_ids = set(invalidate_race_ids or set()) | blocked

        if work.empty or (target_ids is not None and not target_ids):
            out_path = invalidate_daily_feature_races(
                config, date, set(invalidate_race_ids or set()) | blocked
            )
            raise HorseNumberNotReadyError(
                f"{REASON_HORSE_NUMBER_NOT_READY}: no races eligible for Feature CSV",
                blocked_race_ids=sorted(blocked),
                integrity=integrity,
                out_path=out_path,
            )

    races_df = None
    if not work.empty:
        meta_cols = ["race_id", "race_name", "target_surface", "target_distance", "turn", "weather", "track_condition"]
        present = [c for c in meta_cols if c in work.columns]
        if present:
            races_df = work[present].drop_duplicates(subset=["race_id"], keep="last")

    features_df = build_features(work, history_df, races_df)

    baseline_path = daily_features_path(config, date)
    existing = None
    if target_ids is not None and baseline_path.is_file():
        existing = pd.read_csv(baseline_path, encoding="utf-8-sig", low_memory=False)

    merged = merge_daily_features(existing, features_df, target_ids)
    if invalidate_race_ids:
        merged = purge_feature_race_ids(merged, set(invalidate_race_ids))

    out_path = features_output_path(config, date)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


class HorseNumberNotReadyError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        blocked_race_ids: list[str] | None = None,
        integrity: Any = None,
        out_path: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.blocked_race_ids = list(blocked_race_ids or [])
        self.integrity = integrity
        self.out_path = out_path


def verify_feature_loader(race_ids: list[str], config: RefreshConfig) -> list[str]:
    errors: list[str] = []
    ai_root = _resolve_ai_platform_root()
    if ai_root is None:
        return ["AI platform root not found"]
    ai_root_str = str(ai_root)
    if ai_root_str not in sys.path:
        sys.path.insert(0, ai_root_str)
    try:
        from ai_platform.core.features.feature_loader import FeatureLoader, get_last_failure_reason
    except Exception as exc:
        return [f"FeatureLoader import failed: {exc}"]

    loader_root = config.features_shadow_dir or config.data_root
    loader = FeatureLoader(data_root=loader_root)
    for race_id in race_ids:
        result = loader.load(race_id)
        if result is None or result.frame.empty:
            errors.append(f"{race_id}: {get_last_failure_reason() or 'load_failed'}")
    return errors


def run_refresh(
    date: str,
    *,
    config: RefreshConfig | None = None,
    now: datetime | None = None,
    force: bool = False,
    client: NetkeibaClient | None = None,
    logger: Callable[[str], None] | None = None,
) -> RefreshReport:
    cfg = config or RefreshConfig.from_env()
    current = now or now_jst()
    log = logger or print

    report = RefreshReport(
        date=date,
        started_at=current.isoformat(),
        in_window=in_refresh_window(
            current,
            start_hour=cfg.window_start_hour,
            end_hour=cfg.window_end_hour,
        ),
    )

    if not force and not report.in_window:
        report.finished_at = now_jst().isoformat()
        for line in report.log_lines():
            log(line)
        log("[race-refresh] skipped: outside refresh window")
        return report

    net_client = client or NetkeibaClient(min_interval_sec=cfg.min_interval_sec)
    snapshot = load_snapshot(cfg, date)

    try:
        meetings, published, skipped_unpublished = discover_published_races(net_client, date)
    except Exception as exc:
        report.error_count = 1
        report.errors.append(f"discover_failed: {exc}")
        report.finished_at = now_jst().isoformat()
        return report

    report.meeting_count = len(meetings)
    report.listed_count = len(published) + skipped_unpublished
    report.published_count = len(published)
    report.skipped_unpublished = skipped_unpublished

    to_update, unchanged = select_races_for_update(published, snapshot)
    report.skipped_unchanged = unchanged

    if not to_update:
        report.finished_at = now_jst().isoformat()
        for line in report.log_lines():
            log(line)
        log("[race-refresh] no updates required")
        return report

    all_new_runners: list[dict[str, Any]] = []
    all_new_history: list[dict[str, Any]] = []
    replace_ids: set[str] = set()

    for race in to_update:
        race_id = race["race_id"]
        replace_ids.add(race_id)
        try:
            runners, history_rows, _meta = process_race_pipeline(net_client, race, date)
            if not runners:
                report.error_count += 1
                report.errors.append(f"{race_id}: empty_runners")
                continue
            all_new_runners.extend(runners)
            all_new_history.extend(history_rows)
            snapshot[race_id] = RaceSnapshotEntry(
                race_id=race_id,
                numeric_race_id=race["numeric_race_id"],
                course=race["course"],
                race_number=int(race["race_number"]),
                fingerprint=race["fingerprint"],
                features_ok=False,
                updated_at=now_jst().isoformat(),
            )
            report.updated_count += 1
            report.processed_race_ids.append(race_id)
        except Exception as exc:
            report.error_count += 1
            report.errors.append(f"{race_id}: {type(exc).__name__}: {exc}")

    if not all_new_runners:
        report.finished_at = now_jst().isoformat()
        save_snapshot(cfg, date, snapshot)
        return report

    runners_df, history_df = merge_day_frames(cfg, date, replace_ids, all_new_runners, all_new_history)
    _day_dir(cfg, date).mkdir(parents=True, exist_ok=True)
    runners_df.to_csv(_runners_path(cfg, date), index=False, encoding="utf-8-sig")
    history_df.to_csv(_history_path(cfg, date), index=False, encoding="utf-8-sig")

    integrity = validate_runners_horse_number_integrity(
        runners_df,
        date=date,
        race_ids=set(report.processed_race_ids),
    )
    integrity_path = write_integrity_report(
        integrity,
        _day_dir(cfg, date) / "logs" / f"horse_number_integrity_{date}.json",
    )
    report.horse_number_integrity_path = str(integrity_path)
    report.feature_ready_race_ids = list(integrity.ready_race_ids)
    report.feature_blocked_race_ids = list(integrity.blocked_race_ids)
    report.features_skipped_horse_number = len(integrity.blocked_race_ids)
    for line in integrity.log_lines:
        log(line)
        report.errors.append(line.replace("[race-refresh] ", "", 1))
    if integrity.blocked_race_ids:
        report.error_count += len(integrity.blocked_race_ids)
        log(
            f"[race-refresh] {REASON_INCOMPLETE}: "
            f"blocked={len(integrity.blocked_race_ids)} ready={len(integrity.ready_race_ids)}"
        )

    try:
        if integrity.ready_race_ids:
            out_path = write_daily_features(
                cfg,
                date,
                runners_df,
                history_df,
                updated_race_ids=set(integrity.ready_race_ids),
                invalidate_race_ids=set(integrity.blocked_race_ids),
                require_horse_number_integrity=True,
            )
            report.daily_features_path = str(out_path)
            report.features_generated = len(integrity.ready_race_ids)
            loader_errors = verify_feature_loader(integrity.ready_race_ids, cfg)
            if loader_errors:
                report.error_count += len(loader_errors)
                report.errors.extend(loader_errors)
                bad = {e.split(":", 1)[0] for e in loader_errors}
                for race_id in integrity.ready_race_ids:
                    if race_id in snapshot and race_id not in bad:
                        snapshot[race_id].features_ok = True
            else:
                for race_id in integrity.ready_race_ids:
                    if race_id in snapshot:
                        snapshot[race_id].features_ok = True
        else:
            # No formal horse_number races → do not generate Feature CSV rows for them.
            out_path = invalidate_daily_feature_races(
                cfg, date, set(integrity.blocked_race_ids)
            )
            report.daily_features_path = str(out_path)
            report.features_generated = 0
            log(f"[race-refresh] {REASON_HORSE_NUMBER_NOT_READY}: Feature CSV generation skipped")
        for race_id in integrity.blocked_race_ids:
            if race_id in snapshot:
                snapshot[race_id].features_ok = False
    except HorseNumberNotReadyError as exc:
        report.error_count += 1
        report.errors.append(f"features_write: {exc}")
        report.daily_features_path = str(exc.out_path or "")
        log(f"[race-refresh] {REASON_HORSE_NUMBER_NOT_READY}: {exc}")
        for race_id in integrity.blocked_race_ids:
            if race_id in snapshot:
                snapshot[race_id].features_ok = False
    except Exception as exc:
        report.error_count += 1
        report.errors.append(f"features_write: {type(exc).__name__}: {exc}")

    save_snapshot(cfg, date, snapshot)
    report.finished_at = now_jst().isoformat()

    for line in report.log_lines():
        log(line)
    if report.errors:
        for err in report.errors[:20]:
            log(f"[race-refresh] error: {err}")

    return report


def write_report_json(report: RefreshReport, config: RefreshConfig) -> Path:
    out_dir = _day_dir(config, report.date) / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = report.started_at.replace(":", "").replace("+", "_")
    path = out_dir / f"refresh_{ts}.json"
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    latest = out_dir / "refresh_latest.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path


__all__ = [
    "HorseNumberNotReadyError",
    "RefreshConfig",
    "RefreshReport",
    "RaceSnapshotEntry",
    "compute_entries_fingerprint",
    "daily_features_path",
    "discover_published_races",
    "features_output_path",
    "in_refresh_window",
    "invalidate_daily_feature_races",
    "load_snapshot",
    "merge_daily_features",
    "merge_day_frames",
    "run_refresh",
    "select_races_for_update",
    "write_daily_features",
    "write_report_json",
]
