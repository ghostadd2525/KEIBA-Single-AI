# -*- coding: utf-8 -*-
"""PI API parse + Collector contract tests."""
from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WIN5_ROOT = ROOT.parent / "win5-ai"
if WIN5_ROOT.is_dir() and str(WIN5_ROOT) not in sys.path:
    sys.path.insert(0, str(WIN5_ROOT))

from pi_keibanet.netkeiba.parse import (
    find_numeric_race_id,
    parse_entries_from_shutuba,
    parse_race_meta_from_shutuba,
    parse_track_condition,
)
from pi_keibanet.server import Handler
from pi_keibanet.service import PiKeibaNetService


class StubClient:
    def __init__(self, list_html: str, shutuba_html: str) -> None:
        self.list_html = list_html
        self.shutuba_html = shutuba_html

    def fetch_race_list(self, date_yyyy_mm_dd: str) -> str:
        return self.list_html

    def fetch_shutuba(self, numeric_race_id: str) -> str:
        return self.shutuba_html


class ParseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.list_html = (FIX / "race_list_niigata.html").read_text(encoding="utf-8")
        self.shutuba_html = (FIX / "shutuba_sample.html").read_text(encoding="utf-8")

    def test_find_numeric_race_id(self) -> None:
        rid = find_numeric_race_id(self.list_html, date="2026-07-25", venue="新潟", race_no=1)
        self.assertEqual(rid, "202604070101")

    def test_race_meta_contract(self) -> None:
        payload = parse_race_meta_from_shutuba(
            self.shutuba_html,
            date="2026-07-25",
            venue="新潟",
            race_no=1,
            numeric_race_id="202604070101",
        )
        for key in ("race_id", "date", "venue", "race_no", "distance"):
            self.assertIn(key, payload)
        self.assertEqual(payload["distance"], 1600)
        self.assertEqual(payload["race_id"], "20260725_01_新潟")

    def test_entries_core_contract(self) -> None:
        entries = parse_entries_from_shutuba(self.shutuba_html)
        self.assertEqual(len(entries), 2)
        for key in ("horse_number", "frame", "horse_name", "jockey", "weight"):
            self.assertIn(key, entries[0])

    def test_track_condition(self) -> None:
        self.assertEqual(parse_track_condition(self.shutuba_html), "良")

    def test_20260725_construct_race_id(self) -> None:
        html = (FIX / "race_list_20260725_sub.html").read_text(encoding="utf-8")
        self.assertEqual(
            find_numeric_race_id(html, date="2026-07-25", venue="新潟", race_no=1),
            "202604020101",
        )
        self.assertEqual(
            find_numeric_race_id(html, date="2026-07-25", venue="新潟", race_no=6),
            "202604020106",
        )

    def test_shutuba_horse_list_parser(self) -> None:
        html = (FIX / "shutuba_202604020106.html").read_text(encoding="utf-8")
        entries = parse_entries_from_shutuba(html)
        self.assertGreaterEqual(len(entries), 10)
        self.assertTrue(all(e.get("horse_name") for e in entries))


class HttpApiTest(unittest.TestCase):
    def setUp(self) -> None:
        svc = PiKeibaNetService(
            client=StubClient(
                (FIX / "race_list_niigata.html").read_text(encoding="utf-8"),
                (FIX / "shutuba_sample.html").read_text(encoding="utf-8"),
            )
        )
        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.service = svc  # type: ignore[attr-defined]
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.port}"

    def tearDown(self) -> None:
        self.httpd.shutdown()

    def _get(self, path: str) -> tuple[int, dict]:
        import urllib.request

        with urllib.request.urlopen(self.base + path, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return int(resp.status), body

    def test_race_meta_endpoint(self) -> None:
        status, body = self._get(
            "/v1/static/race_meta?date=2026-07-25&venue=%E6%96%B0%E6%BD%9F&race_no=1"
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["venue"], "新潟")

    def test_entries_core_endpoint(self) -> None:
        status, body = self._get(
            "/v1/static/entries_core?date=2026-07-25&venue=%E6%96%B0%E6%BD%9F&race_no=1"
        )
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(body["entries"]), 1)


class CollectorIntegrationTest(unittest.TestCase):
    def test_collector_validates_pi_payload(self) -> None:
        from app.data.collect import validate_entries_core, validate_race_meta

        shutuba = (FIX / "shutuba_sample.html").read_text(encoding="utf-8")
        meta = parse_race_meta_from_shutuba(
            shutuba,
            date="2026-07-25",
            venue="新潟",
            race_no=1,
            numeric_race_id="202604070101",
        )
        entries = {
            "race_id": meta["race_id"],
            "date": "2026-07-25",
            "venue": "新潟",
            "race_no": 1,
            "entries": [
                {k: v for k, v in row.items() if not str(k).startswith("_")}
                for row in parse_entries_from_shutuba(shutuba)
            ],
        }
        rm = validate_race_meta(http_ok=True, body=json.dumps(meta, ensure_ascii=False).encode())
        ec = validate_entries_core(http_ok=True, body=json.dumps(entries, ensure_ascii=False).encode())
        self.assertTrue(rm.ok, rm.errors)
        self.assertTrue(ec.ok, ec.errors)


if __name__ == "__main__":
    unittest.main()
