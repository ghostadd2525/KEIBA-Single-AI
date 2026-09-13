"""
WIN5 AI — PredictionBundle を共通契約とするドメイン HTTP API
+ Conversation Layer / Diagnostics / DB health
"""
from __future__ import annotations

import json
import os
import re
import time
import traceback
import uuid
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
from .user import get_service as get_user_service
from .user.auth import UserAuth

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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
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

    def _user_auth(self) -> tuple[Any | None, tuple[int, dict[str, Any]] | None]:
        auth = UserAuth()
        ctx = auth.authenticate(self.headers.get("Authorization"))
        if not ctx:
            return None, err("UNAUTHORIZED", "Bearer token required", 401)
        return ctx, None

    def do_GET(self) -> None:  # noqa: N802
        """Version8.9.1: never Empty-reply — uncaught errors → HTTP 500 JSON."""
        try:
            self._do_GET_impl()
        except Exception as exc:
            trace_id = str(uuid.uuid4())
            print(
                f"[GET ERROR] trace_id={trace_id} path={getattr(self, '_request_path', self.path)} "
                f"{type(exc).__name__}: {exc}"
            )
            traceback.print_exc()
            try:
                self._send(
                    500,
                    {
                        "ok": False,
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": str(exc) or type(exc).__name__,
                            "trace_id": trace_id,
                        },
                    },
                )
            except Exception as send_exc:
                # Headers may already be partially sent; last-resort log only.
                print(f"[GET ERROR] failed to send 500 JSON trace_id={trace_id}: {send_exc}")

    def _do_GET_impl(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        self._begin_request(path)

        if path == "/health":
            from .ops.run_recovery import collect_result_automation_health

            ra_health = collect_result_automation_health()
            self._send(
                200,
                {
                    "status": "ok",
                    "db": str(app_db.db_path()),
                    "fallback_reasons": list(FALLBACK_REASONS),
                    "result_automation": {
                        "ok": ra_health.get("ok"),
                        "status": ra_health.get("status"),
                        "issues": ra_health.get("issues") or [],
                        "stale_active": len(
                            (ra_health.get("detail") or {}).get("stale_active") or []
                        ),
                        "failed_latest": len(
                            (ra_health.get("detail") or {}).get("failed_latest") or []
                        ),
                        "degraded_latest": len(
                            (ra_health.get("detail") or {}).get("degraded_latest") or []
                        ),
                        "manifest_missing": len(
                            (ra_health.get("detail") or {}).get("manifest_missing") or []
                        ),
                        "summary_missing": len(
                            (ra_health.get("detail") or {}).get("summary_missing") or []
                        ),
                    },
                },
            )
            return

        bad = self._check_key()
        if bad:
            self._send(bad[0], bad[1])
            return

        # A1 Service Integration — Single AI HTTP Application (library facade)
        from .service_integration.handlers import try_dispatch_get as si_try_get
        from .site_integration.handlers import try_dispatch_get as site_try_get
        from .ui_adaptation.handlers import try_dispatch_get as ui_try_get

        ui_get = ui_try_get(path)
        if ui_get is not None:
            self._send(ui_get[0], ui_get[1])
            return

        site_get = site_try_get(path)
        if site_get is not None:
            self._send(site_get[0], site_get[1])
            return

        si_get = si_try_get(path)
        if si_get is not None:
            self._send(si_get[0], si_get[1])
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
            auth = UserAuth()
            ctx = auth.authenticate(self.headers.get("Authorization"))
            if ctx:
                get_user_service().record_prediction_view(
                    ctx.user_id,
                    race_id=race_id,
                    engine_source=(meta or {}).get("engine_source"),
                    feature_source=(meta or {}).get("feature_source"),
                    meta={"source": "prediction_get"},
                )
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

        if path == "/v1/conversation/health":
            from .ops.conversation_observability import build_component_health

            # Additive Observability health (Platform health embedded; structure unchanged)
            self._send(
                200,
                ok(
                    build_component_health(),
                    {"service": "ConversationObservability", "platform": "v4"},
                ),
            )
            return

        if path == "/v1/ops/conversation/metrics":
            from .ops.conversation_observability import get_observability

            self._send(
                200,
                ok(get_observability().snapshot(), {"service": "ConversationObservability"}),
            )
            return

        if path == "/v1/ops/conversation/dashboard":
            from .ops.conversation_observability import dashboard_payload

            self._send(
                200,
                ok(dashboard_payload(), {"service": "ConversationObservability"}),
            )
            return

        if path == "/v1/ops/conversation/alerts":
            from .ops.conversation_observability import evaluate_alerts

            self._send(
                200,
                ok({"alerts": evaluate_alerts()}, {"service": "ConversationObservability"}),
            )
            return

        if path == "/v1/stats/heatmap":
            from .stats.service import get_stats_service

            venues_raw = (qs.get("venues") or [""])[0] or ""
            venue_filter = [v.strip() for v in venues_raw.split(",") if v.strip()] or None
            data = get_stats_service().get_heatmap_stats(
                venues=venue_filter,
            )
            self._send(200, ok(data, {"service": "StatsHeatmap"}))
            return

        if path == "/v1/stats/summary":
            from .stats.service import get_stats_service

            period = (qs.get("period") or ["overall"])[0] or "overall"
            data = get_stats_service().get_summary(period=period)
            # Present as AI-wide stats (not user P&L)
            payload = {
                **data,
                "ai_hit_rate": data.get("hit_rate"),
                "ai_top3_rate": data.get("top3_rate"),
                "ai_hit_at_5_rate": data.get("hit_at_5_rate"),
                "ai_roi": data.get("roi"),
                "ai_profit": None,
                "scope": "global_ai",
            }
            self._send(200, ok(payload, {"service": "StatsSummary"}))
            return

        if path == "/v1/user/progress":
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            self._send(
                200,
                ok(get_user_service().get_progress(ctx.user_id), {"service": "UserService"}),
            )
            return

        if path == "/v1/challenge/monthly":
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            month = (qs.get("month") or [""])[0] or ""
            if not month:
                from datetime import datetime, timezone

                month = datetime.now(timezone.utc).strftime("%Y-%m")
            if len(month) != 7 or month[4] != "-":
                self._send(*err("BAD_REQUEST", "month must be YYYY-MM", 400))
                return
            # Lazy settle user purchases before compare
            try:
                get_user_service().settle_pending_race_results(ctx.user_id)
            except Exception:
                pass
            from .challenge import get_challenge_service

            payload = get_challenge_service().compare(ctx.user_id, month)
            self._send(200, ok(payload, {"service": "ChallengeCompare"}))
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

        if path == "/v1/admin/results/status":
            from .ops.result_automation import get_result_automation

            race_date = (qs.get("date") or qs.get("race_date") or [""])[0] or None
            pipeline = get_result_automation().get_pipeline_status(race_date)
            health = pipeline.get("health") or {}
            if race_date:
                health = {
                    **health,
                    "filter_date": race_date,
                    "detail": {
                        **(health.get("detail") or {}),
                        "stale_active": [
                            x
                            for x in ((health.get("detail") or {}).get("stale_active") or [])
                            if x.get("race_date") == race_date
                        ],
                        "failed_latest": [
                            x
                            for x in ((health.get("detail") or {}).get("failed_latest") or [])
                            if x.get("race_date") == race_date
                        ],
                        "degraded_latest": [
                            x
                            for x in ((health.get("detail") or {}).get("degraded_latest") or [])
                            if x.get("race_date") == race_date
                        ],
                        "manifest_missing": [
                            x
                            for x in ((health.get("detail") or {}).get("manifest_missing") or [])
                            if x.get("race_date") == race_date
                        ],
                        "summary_missing": [
                            x
                            for x in ((health.get("detail") or {}).get("summary_missing") or [])
                            if x.get("race_date") == race_date
                        ],
                    },
                }
            self._send(
                200,
                ok(
                    {
                        **health,
                        "pipeline": pipeline,
                        "stages": pipeline.get("stages") or [],
                        "settlement": pipeline.get("settlement"),
                        "archive": pipeline.get("archive"),
                        "run": pipeline.get("run"),
                        "v71": __import__(
                            "app.ops.ra_cadence", fromlist=["collect_v71_ops_metrics"]
                        ).collect_v71_ops_metrics(race_date),
                    },
                    {"service": "ResultAutomationHealth"},
                ),
            )
            return

        if path == "/v1/admin/ops/v71-metrics":
            from .ops.ra_cadence import collect_v71_ops_metrics

            race_date = (qs.get("date") or qs.get("race_date") or [""])[0] or None
            self._send(
                200,
                ok(collect_v71_ops_metrics(race_date), {"service": "OpsV71Metrics"}),
            )
            return

        if path == "/v1/admin/approvals":
            from .ops.approval_workflow import list_approvals

            status = (qs.get("status") or [""])[0] or None
            self._send(200, ok(list_approvals(status), {"service": "ApprovalQueue"}))
            return

        if path == "/v1/results/day-archive":
            # Client cache purge signal (no PII). Auth optional via BFF.
            from .ops.result_automation import get_result_automation

            race_date = (qs.get("date") or qs.get("race_date") or [""])[0] or None
            if not race_date:
                self._send(*err("BAD_REQUEST", "date required", 400))
                return
            pipeline = get_result_automation().get_pipeline_status(race_date)
            archive = pipeline.get("archive") or {}
            self._send(
                200,
                ok(
                    {
                        "race_date": race_date,
                        "archived": bool(archive),
                        "archive": archive,
                        "run_status": (pipeline.get("run") or {}).get("status"),
                        "client_purge": (archive or {}).get("client_purge"),
                    },
                    {"service": "RaceDayArchive"},
                ),
            )
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

        if path == "/v1/admin/research/evidence/monitoring":
            from .research.api import get_evidence_monitoring

            self._send(200, ok(get_evidence_monitoring(), {"service": "ResearchEvidence"}))
            return

        if path == "/v1/admin/research/resolver/dashboard":
            from .research.api import get_resolver_dashboard

            self._send(200, ok(get_resolver_dashboard(), {"service": "ShadowResolver"}))
            return

        if path == "/v1/admin/research/resolver/governance":
            from .research.api import get_resolver_governance_dashboard

            self._send(
                200,
                ok(get_resolver_governance_dashboard(), {"service": "ResolverGovernance"}),
            )
            return

        if path == "/v1/admin/research/prediction-corpus":
            from .research.api import get_prediction_corpus_summary

            self._send(
                200,
                ok(get_prediction_corpus_summary(), {"service": "PredictionCorpus"}),
            )
            return

        m_snap = re.fullmatch(r"/v1/research/prediction-snapshots/(\d+)", path)
        if m_snap:
            from .research.api import get_prediction_snapshot

            snap = get_prediction_snapshot(int(m_snap.group(1)))
            if not snap:
                self._send(404, {"ok": False, "error": {"code": "NOT_FOUND", "message": "snapshot not found"}})
                return
            self._send(200, ok(snap, {"service": "ResearchEvidence"}))
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

        if path == "/v1/users/me":
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            svc = get_user_service()
            self._send(200, ok(svc.get_me(ctx.user_id), {"service": "UserService"}))
            return

        if path == "/v1/favorites":
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            svc = get_user_service()
            self._send(200, ok(svc.list_favorites(ctx.user_id), {"service": "UserService"}))
            return

        if path == "/v1/user-race-results":
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            view = (qs.get("view") or [""])[0] or ""
            if view in ("history", "accordion", "all"):
                payload = get_user_service().purchase_history(ctx.user_id)
                self._send(200, ok(payload, {"service": "UserService"}))
                return
            month = (qs.get("month") or [""])[0] or ""
            if not month:
                from datetime import datetime, timezone

                month = datetime.now(timezone.utc).strftime("%Y-%m")
            try:
                payload = get_user_service().monthly_race_results(ctx.user_id, month)
                self._send(200, ok(payload, {"service": "UserService"}))
            except ValueError as exc:
                self._send(*err("BAD_REQUEST", str(exc), 400))
            return

        m_urr = re.fullmatch(r"/v1/user-race-results/([^/]+)", path)
        if m_urr:
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            race_id = m_urr.group(1)
            self._send(
                200,
                ok(
                    get_user_service().get_race_result(ctx.user_id, race_id),
                    {"service": "UserService"},
                ),
            )
            return

        m_off = re.fullmatch(r"/v1/races/([^/]+)/official-result", path)
        if m_off:
            try:
                payload = get_user_service().official_race_result(m_off.group(1))
                self._send(200, ok(payload, {"service": "UserService"}))
            except LookupError:
                self._send(*err("NOT_FOUND", "official result not found", 404))
            return

        if path == "/v1/history":
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            limit = int((qs.get("limit") or ["50"])[0])
            svc = get_user_service()
            self._send(
                200,
                ok(svc.list_history(ctx.user_id, limit=limit), {"service": "UserService"}),
            )
            return

        if path == "/v1/chat":
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            session_id = (qs.get("session_id") or [""])[0] or None
            svc = get_user_service()
            self._send(
                200,
                ok(
                    svc.list_chat(ctx.user_id, session_id=session_id),
                    {"service": "UserService"},
                ),
            )
            return

        if path == "/v1/admin/users":
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            svc = get_user_service()
            self._send(200, ok(svc.admin_summary(), {"service": "UserService"}))
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

        # I1 Existing Site Integration + A1 Service Integration + UI1 View Mapper
        from .service_integration.config import SingleServiceConfig
        from .service_integration.handlers import try_dispatch_post as si_try_post
        from .site_integration.config import SiteIntegrationConfig
        from .site_integration.handlers import try_dispatch_post as site_try_post
        from .ui_adaptation.handlers import try_dispatch_post as ui_try_post

        header_timeout = None
        raw_to = self.headers.get("X-Request-Timeout-Ms")
        if raw_to:
            try:
                header_timeout = int(raw_to)
            except ValueError:
                header_timeout = None

        if path.startswith("/v1/ui/"):
            ui_post = ui_try_post(
                path,
                body if isinstance(body, dict) else None,
                authorized=True,
            )
            if ui_post is not None:
                self._send(ui_post[0], ui_post[1])
                return

        if path.startswith("/v1/site/"):
            site_cfg = SiteIntegrationConfig.from_env()
            if length > site_cfg.max_body_bytes:
                self._send(*err("PAYLOAD_TOO_LARGE", "request body exceeds limit", 413))
                return
            site_post = site_try_post(
                path,
                body if isinstance(body, dict) else None,
                authorized=True,
                cfg=site_cfg,
                header_timeout_ms=header_timeout,
            )
            if site_post is not None:
                self._send(site_post[0], site_post[1])
                return

        if path.startswith("/v1/single/"):
            cfg = SingleServiceConfig.from_env()
            if length > cfg.max_body_bytes:
                self._send(*err("PAYLOAD_TOO_LARGE", "request body exceeds limit", 413))
                return
            si_post = si_try_post(
                path,
                body if isinstance(body, dict) else None,
                authorized=True,
                cfg=cfg,
            )
            if si_post is not None:
                self._send(si_post[0], si_post[1])
                return

        if path == "/v1/kaoba/chat":
            self._send(200, ok(kaoba_adapter.generate_reply(body if isinstance(body, dict) else {})))
            return

        if path in ("/v1/conversation/chat", "/v1/conversation"):
            auth = UserAuth()
            ctx = auth.authenticate(self.headers.get("Authorization"))
            if ctx:
                body = dict(body if isinstance(body, dict) else {})
                body["_user_id"] = ctx.user_id
            t0 = time.perf_counter()
            result = conversation.chat(body if isinstance(body, dict) else {})
            latency_ms = (time.perf_counter() - t0) * 1000.0
            try:
                from .ops.conversation_observability import get_observability

                get_observability().record_response(
                    result if isinstance(result, dict) else {},
                    latency_ms=latency_ms,
                )
            except Exception:
                pass
            meta = {
                "service": "ConversationService",
                "layer": "conversation",
            }
            if result.get("orchestrator"):
                meta["service"] = "ConversationOrchestrator"
                meta["platform"] = "v4"
                meta["agent"] = result.get("agent")
            self._send(200, ok(result, meta))
            return

        if path == "/v1/auth/login":
            login_id = str(body.get("login_id") or body.get("id") or "")
            password = str(body.get("password") or "")
            try:
                payload = get_user_service().login(login_id, password)
                self._send(200, ok(payload, {"service": "UserService"}))
            except PermissionError:
                self._send(*err("UNAUTHORIZED", "invalid credentials", 401))
            return

        if path == "/v1/auth/logout":
            payload = get_user_service().logout(self.headers.get("Authorization"))
            self._send(200, ok(payload, {"service": "UserService"}))
            return

        if path == "/v1/auth/setup":
            try:
                payload = get_user_service().setup_user(
                    login_id=str(body.get("login_id") or ""),
                    password=str(body.get("password") or ""),
                    display_name=body.get("display_name"),
                    invite_id=body.get("invite_id"),
                    terms_version=body.get("terms_version"),
                )
                self._send(200, ok(payload, {"service": "UserService"}))
            except ValueError as exc:
                self._send(*err("BAD_REQUEST", str(exc), 400))
            return

        if path == "/v1/favorites":
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            svc = get_user_service()
            self._send(200, ok(svc.add_favorite(ctx.user_id, body), {"service": "UserService"}))
            return

        if path == "/v1/user-race-results":
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            try:
                action = str((body or {}).get("action") or "snapshot")
                ip = self.headers.get("X-Forwarded-For") or self.client_address[0]
                ua = self.headers.get("User-Agent")
                if action == "purchase":
                    payload = get_user_service().register_purchase(
                        ctx.user_id,
                        body if isinstance(body, dict) else {},
                        ip_address=ip,
                        user_agent=ua,
                    )
                else:
                    payload = get_user_service().save_race_strategy_snapshot(
                        ctx.user_id, body if isinstance(body, dict) else {}
                    )
                self._send(200, ok(payload, {"service": "UserService"}))
            except ValueError as exc:
                self._send(*err("BAD_REQUEST", str(exc), 400))
            return

        if path == "/v1/user-race-results/settle-pending":
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            ip = self.headers.get("X-Forwarded-For") or self.client_address[0]
            ua = self.headers.get("User-Agent")
            payload = get_user_service().settle_pending_race_results(
                ctx.user_id, ip_address=ip, user_agent=ua
            )
            self._send(200, ok(payload, {"service": "UserService"}))
            return

        m_settle = re.fullmatch(r"/v1/user-race-results/([^/]+)/settle", path)
        if m_settle:
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            try:
                ip = self.headers.get("X-Forwarded-For") or self.client_address[0]
                ua = self.headers.get("User-Agent")
                payload = get_user_service().settle_race_result(
                    ctx.user_id,
                    m_settle.group(1),
                    body if isinstance(body, dict) else {},
                    ip_address=ip,
                    user_agent=ua,
                )
                self._send(200, ok(payload, {"service": "UserService"}))
            except LookupError as exc:
                self._send(*err("NOT_FOUND", str(exc), 404))
            return

        if path == "/v1/admin/migrate":
            applied = app_db.migrate()
            self._send(200, ok({"applied": applied, "db": str(app_db.db_path())}))
            return

        if path == "/v1/admin/stats/import-baseline":
            from .stats.baseline_import import import_baseline_evaluations

            force = bool(body.get("force")) if isinstance(body, dict) else False
            result = import_baseline_evaluations(force=force)
            self._send(200, ok(result, {"service": "BaselineImport"}))
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

        if path == "/v1/admin/results/run":
            race_date = str(body.get("date") or body.get("race_date") or "").strip()
            if not race_date:
                self._send(*err("BAD_REQUEST", "race_date required", 400))
                return
            from .ops.result_automation import get_result_automation

            trigger = str(body.get("trigger") or body.get("trigger_source") or "manual")
            parent = body.get("parent_run_id")
            parent_run_id = int(parent) if parent is not None and str(parent).isdigit() else None
            force = bool(body.get("force"))
            skip_sync = bool(body.get("skip_result_sync"))
            evidence_only = bool(body.get("evidence_only"))
            result = get_result_automation().run(
                race_date,
                trigger=trigger,
                parent_run_id=parent_run_id,
                force=force,
                skip_result_sync=skip_sync,
                evidence_only=evidence_only,
            )
            self._send(200, ok(result, {"service": "ResultAutomation"}))
            return

        # Version8.8 Approval Workflow (Deploy Note only; PE/CE/AI untouched)
        m_appr = re.match(r"^/v1/admin/approvals/([^/]+)/(approve|reject)$", path)
        if m_appr:
            from .ops.approval_workflow import approve, reject

            approval_id = m_appr.group(1)
            action = m_appr.group(2)
            actor = str(body.get("actor") or body.get("user_id") or "admin")
            if action == "approve":
                data = approve(approval_id, actor=actor)
                if not data.get("ok"):
                    self._send(
                        *err(
                            "APPROVAL_FAILED",
                            str(data.get("error") or "approve failed"),
                            400,
                        )
                    )
                    return
                self._send(200, ok(data, {"service": "ApprovalQueue"}))
                return
            reason = str(body.get("reason") or "").strip()
            if not reason:
                self._send(*err("BAD_REQUEST", "reject reason required", 400))
                return
            data = reject(approval_id, reason=reason, actor=actor)
            if not data.get("ok"):
                self._send(
                    *err(
                        "APPROVAL_FAILED",
                        str(data.get("error") or "reject failed"),
                        400,
                    )
                )
                return
            self._send(200, ok(data, {"service": "ApprovalQueue"}))
            return

        self._send(*err("NOT_FOUND", "unknown path", 404))

    def do_PATCH(self) -> None:  # noqa: N802
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

        if path == "/v1/users/me":
            ctx, denied = self._user_auth()
            if denied:
                self._send(*denied)
                return
            assert ctx is not None
            svc = get_user_service()
            self._send(
                200,
                ok(svc.patch_me(ctx.user_id, body if isinstance(body, dict) else {}), {"service": "UserService"}),
            )
            return

        self._send(*err("NOT_FOUND", "unknown path", 404))


def main() -> None:
    # ensure DB schema on boot
    try:
        app_db.migrate()
    except Exception as exc:
        print(f"db migrate warning: {exc}")

    # One-time formal research baseline → race_evaluations (AI総合実績 seed)
    try:
        from .stats.baseline_import import ensure_baseline_imported

        bi = ensure_baseline_imported()
        if bi.get("imported"):
            print(
                f"baseline evaluations imported: {bi.get('inserted')} rows "
                f"(hits={bi.get('hits')}/{bi.get('fixture_rows')})"
            )
        elif bi.get("already_imported"):
            print("baseline evaluations already present — skip import")
        elif not bi.get("ok"):
            print(f"baseline import skipped: {bi.get('reason')}")
    except Exception as exc:
        print(f"baseline import warning: {exc}")

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
