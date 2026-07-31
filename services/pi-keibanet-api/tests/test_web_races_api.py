# -*- coding: utf-8 -*-
"""Tests for Web GUI race catalog API."""
from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.race_catalog import (
    assign_venue_label_nos,
    build_race_summary,
    group_races_by_course,
    parse_race_id_ref,
    race_label,
)
from pi_keibanet.server import Handler
from pi_keibanet.service import PiKeibaNetService
from pi_keibanet.netkeiba.parse import parse_list_races_from_race_list


class StubClient:
    def __init__(self, list_html: str, shutuba_html: str = "") -> None:
        self.list_html = list_html
        self.shutuba_html = shutuba_html

    def fetch_race_list(self, date_yyyy_mm_dd: str) -> str:
        return self.list_html

    def fetch_shutuba(self, numeric_race_id: str) -> str:
        return self.shutuba_html


class RaceCatalogUnitTest(unittest.TestCase):
    def test_race_label(self) -> None:
        self.assertEqual(race_label("新潟", 6), "新潟6R")
        self.assertEqual(race_label("札幌", 11), "札幌11R")

    def test_build_race_summary_keeps_identity(self) -> None:
        s = build_race_summary(
            race_id="2026-07-25-01-06",
            race_date="2026-07-25",
            course="新潟",
            race_number=6,
            race_name="豊栄特別",
        )
        for key in ("race_id", "race_date", "course", "race_number", "race_label", "race_name"):
            self.assertIn(key, s)
        self.assertEqual(s["venue"], "新潟")
        self.assertEqual(s["race_no"], 6)
        self.assertEqual(s["race_label"], "新潟6R")

    def test_parse_win5_and_collector(self) -> None:
        w = parse_race_id_ref("2026-07-25-01-06")
        self.assertEqual(w["format"], "win5")
        self.assertEqual(w["race_date"], "2026-07-25")
        self.assertEqual(w["race_number"], 6)
        c = parse_race_id_ref("20260725_06_新潟")
        self.assertEqual(c["format"], "collector")
        self.assertEqual(c["course"], "新潟")
        self.assertEqual(c["race_number"], 6)

    def test_meeting_order_label_nos(self) -> None:
        labels = assign_venue_label_nos(
            ["札幌", "新潟", "中京"],
            preferred_order=["新潟", "中京", "札幌"],
        )
        self.assertEqual(labels["新潟"], 1)
        self.assertEqual(labels["中京"], 2)
        self.assertEqual(labels["札幌"], 3)

    def test_group_by_course(self) -> None:
        races = [
            build_race_summary(race_id="a", race_date="2026-07-25", course="中京", race_number=7),
            build_race_summary(race_id="b", race_date="2026-07-25", course="新潟", race_number=6),
            build_race_summary(race_id="c", race_date="2026-07-25", course="新潟", race_number=8),
        ]
        tree = group_races_by_course(races)
        courses = [v["course"] for v in tree]
        self.assertIn("新潟", courses)
        niigata = next(v for v in tree if v["course"] == "新潟")
        self.assertEqual([r["race_number"] for r in niigata["races"]], [6, 8])

    def test_list_parser_includes_race_name(self) -> None:
        html = (FIX / "race_list_20260725_sub.html").read_text(encoding="utf-8")
        races = parse_list_races_from_race_list(html)
        self.assertTrue(any(r.race_no == 6 and r.venue == "新潟" for r in races))
        hit = next(r for r in races if r.venue == "新潟" and r.race_no == 6)
        self.assertTrue(hit.race_name)
        self.assertEqual(hit.post_time, "15:10")


class WebApiHttpTest(unittest.TestCase):
    def setUp(self) -> None:
        list_html = (FIX / "race_list_20260725_sub.html").read_text(encoding="utf-8")
        shutuba = (FIX / "shutuba_202604020106.html").read_text(encoding="utf-8")
        svc = PiKeibaNetService(client=StubClient(list_html, shutuba))
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

        try:
            with urllib.request.urlopen(self.base + path, timeout=10) as resp:
                return int(resp.status), json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            body = json.loads(exc.read().decode("utf-8"))
            return int(exc.code), body

    def test_list_races_grouped(self) -> None:
        status, body = self._get("/v1/races?date=2026-07-25")
        self.assertEqual(status, 200)
        self.assertEqual(body["date"], "2026-07-25")
        self.assertGreaterEqual(body["count"], 1)
        self.assertTrue(body["venues"])
        courses = [v["course"] for v in body["venues"]]
        self.assertIn("新潟", courses)
        for venue in body["venues"]:
            for race in venue["races"]:
                for key in ("race_id", "race_date", "course", "race_number", "race_label"):
                    self.assertIn(key, race)
                self.assertTrue(str(race["race_label"]).endswith("R"))

    def test_get_race_by_id(self) -> None:
        _, listed = self._get("/v1/races?date=2026-07-25")
        target = next(r for r in listed["races"] if r["course"] == "新潟" and r["race_number"] == 6)
        rid = target["race_id"]
        status, body = self._get(f"/v1/races/{quote(rid)}")
        self.assertEqual(status, 200)
        self.assertEqual(body["race_id"], rid)
        self.assertEqual(body["course"], "新潟")
        self.assertEqual(body["race_number"], 6)
        self.assertEqual(body["race_label"], "新潟6R")
        self.assertIn("race_name", body)

    def test_entries_core_has_display_fields(self) -> None:
        status, body = self._get(
            "/v1/static/entries_core?date=2026-07-25&venue=%E6%96%B0%E6%BD%9F&race_no=6"
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["course"], "新潟")
        self.assertEqual(body["race_number"], 6)
        self.assertEqual(body["race_label"], "新潟6R")
        self.assertEqual(body["venue"], "新潟")
        self.assertEqual(body["race_no"], 6)

    def test_predictions_endpoint_shape(self) -> None:
        _, listed = self._get("/v1/races?date=2026-07-25")
        rid = next(r["race_id"] for r in listed["races"] if r["course"] == "新潟")
        status, body = self._get(f"/v1/predictions/{quote(rid)}")
        self.assertEqual(status, 200)
        self.assertEqual(body["course"], "新潟")
        self.assertIn("race_number", body)
        self.assertIn("race_label", body)
        self.assertIn("prediction_available", body)


if __name__ == "__main__":
    unittest.main()
