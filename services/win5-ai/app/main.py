"""
WIN5 AI — PredictionBundle を共通契約とするドメイン HTTP API
+ Conversation Layer / Diagnostics / DB health
"""
from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import conversation
from .data import db as app_db
from .diagnostics import FALLBACK_REASONS, REASON_HELP, collect_missing_report
from .engine import data as engine
from .engine import domains
from .engine.adapters import analysis_adapter, kaoba_adapter, prediction_adapter

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

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, {})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

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

        if path == "/v1/diagnostics/missing":
            # 最新 list を実行してレポート再生成
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
