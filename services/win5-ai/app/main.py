"""
WIN5 AI — PredictionBundle を共通契約とするドメイン HTTP API
+ Conversation Layer / Diagnostics / DB health
"""
from __future__ import annotations

import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import conversation
from . import core as _core_bridge  # noqa: F401 — FeatureLoader DB bridge
from .data import db as app_db
from .data.coverage import get_coverage
from .data.dashboard import DashboardService
from .data.etl import run_scheduled_etl
from .data.validation import validate_all_races
from .data.race_resolver import resolve_identity
from .diagnostics import FALLBACK_REASONS, REASON_HELP, collect_missing_report
from .engine import data as engine
from .engine import domains
from .engine.adapters import analysis_adapter, kaoba_adapter, prediction_adapter
from .ops.monitoring import MonitoringService
from .ops.performance import record_timing

AI_API_KEY = os.environ.get("AI_API_KEY", "")
HOST = os.environ.get("AI_HOST", "127.0.0.1")
PORT = int(os.environ.get("AI_PORT", "8000"))
AI_ALLOW_PUBLIC_BIND = (os.environ.get("AI_ALLOW_PUBLIC_BIND") or "0").lower() in (
    "1",
    "true",
    "yes",
)


def ok(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """HTTP envelope. meta は運用 provenance（PredictionBundle 契約外）。"""
    payload: dict[str, Any] = {"ok": True, "data": data}
    if meta:
        payload["meta"] = meta
    return payload


def err(code: str, message: str, status: int = 400) -> tuple[int, dict[str, Any]]:
    return status, {"ok": False, "error": {"code": code, "message": message, "details": None}}


class Handler(BaseHTTPRequestHandler):
    server_version = "WIN5-AI/0.4"

    def log_message(self, fmt: str, *args: Any) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def _check_key(self) -> tuple[int, dict[str, Any]] | None:
        if not AI_API_KEY:
            return None
        if self.headers.get("X-AI-Key") != AI_API_KEY:
            return err("UNAUTHORIZED", "invalid AI key", 401)
        return None

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-AI-Key, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        if status != 204:
            self.wfile.write(raw)
        started = getattr(self, "_request_started_at", None)
        if started is not None:
            path = getattr(self, "_request_path", "unknown")
            ms = (time.perf_counter() - started) * 1000
            record_timing("api", path, ms, status="ok" if status < 400 else "error")

    def _begin_request(self, path: str) -> None:
        self._request_started_at = time.perf_counter()
        self._request_path = path

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, {})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        self._begin_request(path)

        if path == "/health":
            self._send(
                200,
                {
                    "status": "ok",
                    "db": str(app_db.db_path()),
                    "fallback_reasons": list(FALLBACK_REASONS),
                },
            )
            return

        bad = self._check_key()
        if bad:
            self._send(bad[0], bad[1])
            return

        if path == "/v1/predictions":
            date = (qs.get("date") or [""])[0] or ""
            venue = (qs.get("venue") or [""])[0] or ""
            items, meta = prediction_adapter.list_with_meta(date=date, venue=venue)
            self._send(200, ok(items, meta))
            return

        m = re.fullmatch(r"/v1/predictions/([^/]+)", path)
        if m:
            race_id = m.group(1)
            bundle, meta = prediction_adapter.get_with_meta(race_id)
            if not bundle:
                self._send(*err("NOT_FOUND", "PredictionBundle not found", 404))
                return
            self._send(200, ok(bundle, meta))
            return

        if path == "/v1/diagnostics/fallback-reasons":
            self._send(
                200,
                ok(
                    {
                        "reasons": list(FALLBACK_REASONS),
                        "help": REASON_HELP,
                    }
                ),
            )
            return

        if path == "/v1/races/resolve":
            text = (qs.get("text") or qs.get("q") or [""])[0]
            ident = resolve_identity(text)
            if not ident:
                self._send(*err("NOT_FOUND", "race not resolved", 404))
                return
            self._send(200, ok(ident.as_meta(), {"service": "RaceResolver"}))
            return

        if path == "/v1/data/coverage":
            race_date = (qs.get("date") or qs.get("race_date") or [""])[0] or None
            cov = get_coverage(race_date=race_date)
            self._send(200, ok(cov, {"service": "Coverage"}))
            return

        if path == "/v1/admin/dashboard":
            race_date = (qs.get("date") or qs.get("race_date") or [""])[0] or None
            dash = DashboardService().summary(race_date=race_date)
            self._send(200, ok(dash, {"service": "Dashboard"}))
            return

        if path == "/v1/admin/etl/status":
            race_date = (qs.get("date") or qs.get("race_date") or [""])[0] or None
            status = DashboardService().etl_status(race_date=race_date)
            self._send(200, ok(status, {"service": "EtlScheduler"}))
            return

        if path == "/v1/admin/etl/history":
            limit = int((qs.get("limit") or ["20"])[0])
            hist = DashboardService().import_history(limit=limit)
            self._send(200, ok(hist, {"service": "ImportHistory"}))
            return

        if path == "/v1/admin/dashboard/fallback":
            fb = DashboardService().fallback_reasons()
            self._send(200, ok(fb, {"service": "FallbackReasons"}))
            return

        if path == "/v1/admin/dashboard/missing":
            missing = DashboardService().missing_data()
            self._send(200, ok(missing, {"service": "MissingData"}))
            return

        if path == "/v1/admin/data/sources":
            from .data.sources import list_sources

            self._send(200, ok(list_sources(), {"service": "DataSources"}))
            return

        if path == "/v1/admin/monitoring":
            metrics = MonitoringService().collect()
            self._send(200, ok(metrics, {"service": "Monitoring"}))
            return

        if path == "/v1/diagnostics/missing":
            _, meta = prediction_adapter.list_with_meta()
            items = meta.get("items") or []
            report = collect_missing_report(items)
            self._send(200, ok(report, {"service": "Diagnostics"}))
            return

        m = re.fullmatch(r"/v1/analysis/([^/]+)", path)
        if m:
            race_id = m.group(1)
            self._send(200, ok(analysis_adapter.get_analysis(race_id)))
            return

        m = re.fullmatch(r"/v1/confidence/([^/]+)", path)
        if m:
            race_id = m.group(1)
            b = prediction_adapter.get_bundle(race_id)
            if not b:
                self._send(*err("NOT_FOUND", "PredictionBundle not found for race_id", 404))
                return
            races = engine.load_races().get("races") or []
            meta = next((r for r in races if r.get("race_id") == race_id), None)
            if meta and meta.get("ai_confidence") is not None:
                b["ai_confidence"] = {
                    **(b.get("ai_confidence") or {}),
                    "score": float(meta["ai_confidence"]) / 100.0,
                    "status": "ok",
                }
            self._send(200, ok(domains.project_confidence(b)))
            return

        m = re.fullmatch(r"/v1/tickets/([^/]+)", path)
        if m:
            race_id = m.group(1)
            bundle = prediction_adapter.get_bundle(race_id)
            if not bundle:
                self._send(*err("NOT_FOUND", "PredictionBundle not found for race_id", 404))
                return
            self._send(200, ok(domains.project_tickets(bundle)))
            return

        self._send(*err("NOT_FOUND", "unknown path", 404))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        self._begin_request(path)

        bad = self._check_key()
        if bad:
            self._send(bad[0], bad[1])
            return

        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(*err("BAD_REQUEST", "JSON body required", 400))
            return

        if path == "/v1/kaoba/chat":
            self._send(200, ok(kaoba_adapter.generate_reply(body if isinstance(body, dict) else {})))
            return

        if path in ("/v1/conversation/chat", "/v1/conversation"):
            result = conversation.chat(body if isinstance(body, dict) else {})
            self._send(
                200,
                ok(
                    result,
                    {
                        "service": "ConversationService",
                        "layer": "conversation",
                    },
                ),
            )
            return

        if path == "/v1/admin/migrate":
            applied = app_db.migrate()
            self._send(200, ok({"applied": applied, "db": str(app_db.db_path())}))
            return

        if path == "/v1/admin/etl/import-day":
            data_dir = str(body.get("data_dir") or "").strip()
            race_date = str(body.get("date") or body.get("race_date") or "").strip() or None
            if not data_dir:
                self._send(*err("BAD_REQUEST", "data_dir required", 400))
                return
            from pathlib import Path

            from .data.etl import import_day as etl_import_day

            result = etl_import_day(Path(data_dir), race_date=race_date)
            engine.clear_caches()
            if race_date:
                validation = validate_all_races(race_date=race_date)
                payload = {"etl": result.as_dict(), "validation": validation}
            else:
                payload = result.as_dict()
            self._send(200, ok(payload, {"service": "EtlPipeline"}))
            return

        if path == "/v1/admin/etl/schedule":
            race_date = str(body.get("date") or body.get("race_date") or "").strip()
            if not race_date:
                self._send(*err("BAD_REQUEST", "race_date required", 400))
                return
            source_type = str(body.get("source_type") or body.get("source") or "").strip() or None
            data_dir = str(body.get("data_dir") or "").strip() or None
            from pathlib import Path

            result = run_scheduled_etl(
                race_date,
                source_type=source_type,
                data_dir=Path(data_dir) if data_dir else None,
            )
            engine.clear_caches()
            self._send(200, ok(result.as_dict(), {"service": "EtlScheduler"}))
            return

        if path == "/v1/admin/validate":
            race_date = str(body.get("date") or body.get("race_date") or "").strip() or None
            validation = validate_all_races(race_date=race_date)
            self._send(200, ok(validation, {"service": "AutoValidation"}))
            return

        self._send(*err("NOT_FOUND", "unknown path", 404))


def main() -> None:
    # ensure DB schema on boot
    try:
        app_db.migrate()
    except Exception as exc:
        print(f"db migrate warning: {exc}")

    host = HOST
    if host in ("0.0.0.0", "::", "[::]") and not AI_ALLOW_PUBLIC_BIND:
        raise SystemExit(
            "Refusing to bind public interface. "
            "Use AI_HOST=127.0.0.1 (default) behind cloudflared, "
            "or set AI_ALLOW_PUBLIC_BIND=1 only for controlled labs."
        )
    server = ThreadingHTTPServer((host, PORT), Handler)
    print(f"WIN5 AI (PredictionBundle + Conversation + DB) on http://{host}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
