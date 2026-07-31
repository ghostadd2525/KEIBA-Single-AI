# -*- coding: utf-8 -*-
"""HTTP server — Collector-compatible + Web GUI KeibaNet PI API."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .service import PiKeibaNetService, RaceNotFoundError
from .netkeiba.client import NetkeibaFetchError

HOST = os.environ.get("PI_KEIBANET_HOST", "0.0.0.0")
PORT = int(os.environ.get("PI_KEIBANET_PORT", "8081"))

_ROUTES = {
    "/v1/static/race_meta": "race_meta",
    "/v1/static/entries_core": "entries_core",
    "/v1/dynamic/odds": "odds",
    "/v1/dynamic/track": "track",
    "/v1/pipeline/entries_full": "entries_full",
}


def _parse_query(qs: dict[str, list[str]]) -> tuple[str, str, int]:
    date = (qs.get("date") or [""])[0].strip()
    venue = (qs.get("venue") or [""])[0].strip()
    race_no_raw = (qs.get("race_no") or ["0"])[0].strip()
    if not date or not venue:
        raise ValueError("date and venue are required")
    try:
        race_no = int(race_no_raw)
    except ValueError as exc:
        raise ValueError("race_no must be integer") from exc
    return date, venue, race_no


class Handler(BaseHTTPRequestHandler):
    server_version = "Expect-PI-KeibaNet/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)
        svc: PiKeibaNetService = self.server.service  # type: ignore[attr-defined]

        if path == "/health":
            self._json(200, {"status": "ok", "service": "pi-keibanet-api"})
            return

        if path == "/v1/ops/cache-metrics":
            from . import cache_metrics

            self._json(200, cache_metrics.snapshot())
            return

        if path == "/v1/ops/horse-number-integrity":
            date = (qs.get("date") or [""])[0].strip()
            try:
                payload = svc.get_horse_number_integrity(date=date)
            except Exception as exc:
                self._json(500, {"error": "integrity_check_failed", "message": str(exc)})
                return
            status = 200 if payload.get("ok") else 503
            self._json(status, payload)
            return

        # --- Web GUI race catalog ---
        if path == "/v1/races":
            date = (qs.get("date") or [""])[0].strip()
            if not date:
                self._json(400, {"error": "bad_request", "message": "date is required"})
                return
            try:
                payload = svc.list_races(date=date)
            except ValueError as exc:
                self._json(400, {"error": "bad_request", "message": str(exc)})
                return
            except NetkeibaFetchError as exc:
                self._json(502, {"error": "html_fetch_failed", "message": str(exc)})
                return
            except Exception as exc:
                self._json(502, {"error": "upstream_error", "message": str(exc)})
                return
            self._json(200, payload)
            return

        if path.startswith("/v1/races/"):
            race_id = unquote(path[len("/v1/races/"):].strip("/"))
            if not race_id:
                self._json(400, {"error": "bad_request", "message": "race_id required"})
                return
            # /v1/races/{id}/board|entries|history
            sub = ""
            if "/" in race_id:
                race_id, sub = race_id.split("/", 1)
                race_id = race_id.strip()
                sub = sub.strip().strip("/")
            enrich = (qs.get("enrich") or ["1"])[0].strip() not in {"0", "false", "no"}
            include_history = (qs.get("include") or [""])[0].strip().lower() in {
                "history",
                "1",
                "true",
                "yes",
            } or (qs.get("history") or [""])[0].strip() in {"1", "true", "yes"}
            try:
                if sub in {"board", "entries"}:
                    payload = svc.get_race_board(
                        race_id,
                        include_history=include_history,
                    )
                    if sub == "entries":
                        payload = {
                            "race_id": payload.get("race_id"),
                            "entries": payload.get("entries") or [],
                            "count": payload.get("count") or 0,
                        }
                elif sub == "history":
                    payload = svc.get_race_history(race_id)
                elif sub in {"odds-series", "odds_series"}:
                    refresh = (qs.get("refresh") or [""])[0].strip() in {"1", "true", "yes"}
                    payload = svc.get_odds_series(race_id, refresh=refresh)
                elif sub == "":
                    payload = svc.get_race(race_id, enrich=enrich)
                else:
                    self._json(404, {"error": "not_found", "path": path})
                    return
            except ValueError as exc:
                self._json(400, {"error": "bad_request", "message": str(exc)})
                return
            except RaceNotFoundError as exc:
                self._json(
                    404,
                    {"error": "race_not_found", "reason": exc.reason, "message": exc.message},
                )
                return
            except NetkeibaFetchError as exc:
                self._json(502, {"error": "html_fetch_failed", "message": str(exc)})
                return
            except Exception as exc:
                self._json(502, {"error": "upstream_error", "message": str(exc)})
                return
            self._json(200, payload)
            return

        if path.startswith("/v1/predictions/"):
            race_id = unquote(path[len("/v1/predictions/"):].strip("/"))
            if not race_id:
                self._json(400, {"error": "bad_request", "message": "race_id required"})
                return
            try:
                payload = svc.get_prediction(race_id)
            except ValueError as exc:
                self._json(400, {"error": "bad_request", "message": str(exc)})
                return
            except RaceNotFoundError as exc:
                self._json(
                    404,
                    {"error": "race_not_found", "reason": exc.reason, "message": exc.message},
                )
                return
            except NetkeibaFetchError as exc:
                self._json(502, {"error": "html_fetch_failed", "message": str(exc)})
                return
            except Exception as exc:
                self._json(502, {"error": "upstream_error", "message": str(exc)})
                return
            self._json(200, payload)
            return

        # --- Collector static/dynamic (date+venue+race_no) ---
        handler_name = _ROUTES.get(path)
        if not handler_name:
            self._json(404, {"error": "not_found", "path": path})
            return
        try:
            date, venue, race_no = _parse_query(qs)
        except ValueError as exc:
            self._json(400, {"error": "bad_request", "message": str(exc)})
            return
        try:
            payload = getattr(svc, handler_name)(date=date, venue=venue, race_no=race_no)
        except RaceNotFoundError as exc:
            self._json(
                404,
                {"error": "race_not_found", "reason": exc.reason, "message": exc.message},
            )
            return
        except NetkeibaFetchError as exc:
            self._json(502, {"error": "html_fetch_failed", "message": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - upstream netkeiba
            self._json(502, {"error": "upstream_error", "message": str(exc)})
            return
        self._json(200, payload)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        svc: PiKeibaNetService = self.server.service  # type: ignore[attr-defined]

        try:
            if path == "/v1/pipeline/horse_history":
                self._handle_horse_history(svc, body)
            elif path == "/v1/pipeline/features":
                self._handle_features(svc, body)
            else:
                self._json(404, {"error": "not_found", "path": path})
        except RaceNotFoundError as exc:
            self._json(404, {"error": "race_not_found", "reason": exc.reason, "message": exc.message})
        except NetkeibaFetchError as exc:
            self._json(502, {"error": "html_fetch_failed", "message": str(exc)})
        except Exception as exc:
            self._json(502, {"error": "upstream_error", "message": str(exc)})

    def _handle_horse_history(self, svc: PiKeibaNetService, body: bytes) -> None:
        payload = json.loads(body.decode("utf-8")) if body else {}
        entries = payload.get("entries", [])
        race_context = payload.get("race_context")
        if not entries:
            self._json(400, {"error": "bad_request", "message": "entries required"})
            return
        rows = svc.horse_history(entries=entries, race_context=race_context)
        self._json(200, {"history_rows": rows, "count": len(rows)})

    def _handle_features(self, svc: PiKeibaNetService, body: bytes) -> None:
        import pandas as pd
        from .features import build_features
        payload = json.loads(body.decode("utf-8")) if body else {}
        runners = payload.get("runners", [])
        history_rows = payload.get("history_rows", [])
        races = payload.get("races")
        if not runners or not history_rows:
            self._json(400, {"error": "bad_request", "message": "runners and history_rows required"})
            return
        runners_df = pd.DataFrame(runners)
        history_df = pd.DataFrame(history_rows)
        races_df = pd.DataFrame(races) if races else None
        result = build_features(runners_df, history_df, races_df)
        self._json(200, {"features": result.to_dict(orient="records"), "count": len(result)})

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def _json_default(obj: Any) -> Any:
    """Serialize numpy / pandas scalars for prediction payloads."""
    try:
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
    except Exception:
        pass
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def serve(host: str = HOST, port: int = PORT) -> None:
    service = PiKeibaNetService()
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.service = service  # type: ignore[attr-defined]
    print(f"PI KeibaNet API listening on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    serve()
