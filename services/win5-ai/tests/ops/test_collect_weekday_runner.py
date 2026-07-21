# -*- coding: utf-8 -*-
"""Smoke test for collect_weekday_runner with mock KeibaNet."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.db import migrate
from app.ops.collect_weekday_runner import run_collect_day


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        date = params.get("date", [""])[0]
        venue = params.get("venue", [""])[0]
        race_no = int(params.get("race_no", ["1"])[0])
        if parsed.path == "/v1/static/race_meta":
            body = json.dumps(
                {
                    "race_id": f"{date.replace('-', '')}_{race_no:02d}_{venue}",
                    "date": date,
                    "venue": venue,
                    "race_no": race_no,
                    "distance": 1600,
                    "surface": "芝",
                    "field_size": 16,
                },
                ensure_ascii=False,
            ).encode("utf-8")
        elif parsed.path == "/v1/static/entries_core":
            body = json.dumps(
                {
                    "race_id": f"{date.replace('-', '')}_{race_no:02d}_{venue}",
                    "date": date,
                    "venue": venue,
                    "race_no": race_no,
                    "entries": [
                        {
                            "horse_number": 1,
                            "frame": 1,
                            "horse_name": "テスト馬A",
                            "jockey": "騎手A",
                            "weight": 55.0,
                        }
                    ],
                },
                ensure_ascii=False,
            ).encode("utf-8")
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)


class CollectWeekdayRunnerTest(unittest.TestCase):
    def test_run_collect_day_mock(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        cal_dir = root / "calendars"
        cal_dir.mkdir()
        cal = {
            "calendar_version": "test-w30",
            "week_id": "2026-07-25",
            "days": [
                {
                    "race_date": "2026-07-25",
                    "venues": {"新潟": 2},
                    "venue_races": {"新潟": [1, 2]},
                }
            ],
        }
        (cal_dir / "week_2026_07_25.json").write_text(
            json.dumps(cal, ensure_ascii=False), encoding="utf-8"
        )

        server = HTTPServer(("127.0.0.1", 0), _Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        os.environ["EXPECT_AI_DB_PATH"] = str(root / "test.db")
        os.environ["EXPECT_COLLECT_MANIFEST_DIR"] = str(root / "manifests")
        os.environ["EXPECT_COLLECT_RAW_DIR"] = str(root / "raw")
        os.environ["EXPECT_COLLECT_COVERAGE_DIR"] = str(root / "coverage")
        os.environ["EXPECT_COLLECT_CALENDAR_DIR"] = str(cal_dir)
        os.environ["EXPECT_COLLECT_DAILY_LIMIT"] = "200"
        os.environ["EXPECT_KEIBANET_BASE_URL"] = f"http://127.0.0.1:{port}"
        os.environ["EXPECT_COLLECT_DRAW_CONFIRMED"] = "1"
        try:
            migrate()
            out = run_collect_day(as_of="2026-07-21", week_id="2026-07-25", force=False)
            self.assertEqual(out["status"], "ok")
            self.assertGreaterEqual(out["collect"]["dequeued"], 1)
            self.assertIn("coverage_path", out)
        finally:
            server.shutdown()
            for key in list(os.environ.keys()):
                if key.startswith("EXPECT_"):
                    os.environ.pop(key, None)
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
