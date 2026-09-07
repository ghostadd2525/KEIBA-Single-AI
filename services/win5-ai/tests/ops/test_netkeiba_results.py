# -*- coding: utf-8 -*-
"""Unit tests for netkeiba result parsing (no network)."""
from __future__ import annotations

import unittest

from app.ops.netkeiba_results import parse_finish_order, parse_payouts, parse_result_html


SAMPLE_HTML = """
<table>
<tr class="HorseList">
  <td class="Result_Num">1</td>
  <td class="Num Waku6">6</td>
  <td class="Num Txt_C">7</td>
  <td class="Horse_Info"><span class="HorseNameSpan">WinnerA</span></td>
</tr>
<tr class="HorseList">
  <td class="Result_Num">2</td>
  <td class="Num Waku6">6</td>
  <td class="Num Txt_C">6</td>
  <td class="Horse_Info"><span class="HorseNameSpan">SecondB</span></td>
</tr>
<tr class="HorseList">
  <td class="Result_Num">3</td>
  <td class="Num Waku4">4</td>
  <td class="Num Txt_C">4</td>
  <td class="Horse_Info"><span class="HorseNameSpan">ThirdC</span></td>
</tr>
</table>
<table class="Payout_Detail_Table">
<tr><th>単勝</th><td>7</td><td>200円</td><td>1人気</td></tr>
<tr><th>複勝</th><td>7 6 4</td><td>110円230円110円</td><td></td></tr>
<tr><th>馬連</th><td>6 7</td><td>1,840円</td><td></td></tr>
</table>
<table class="Payout_Detail_Table">
<tr><th>ワイド</th><td>6 7 4 7 4 6</td><td>450円130円460円</td><td></td></tr>
<tr><th>3連複</th><td>4 6 7</td><td>840円</td><td></td></tr>
<tr><th>3連単</th><td>7 6 4</td><td>5,360円</td><td></td></tr>
</table>
"""


class NetkeibaParseTest(unittest.TestCase):
    def test_finish_order(self):
        self.assertEqual(parse_finish_order(SAMPLE_HTML), [7, 6, 4])

    def test_payouts(self):
        pays = parse_payouts(SAMPLE_HTML)
        self.assertEqual(pays["単勝"]["7"], 200)
        self.assertEqual(pays["馬連"]["6-7"], 1840)
        self.assertEqual(pays["ワイド"]["6-7"], 450)
        self.assertEqual(pays["三連複"]["4-6-7"], 840)
        self.assertEqual(pays["三連単"]["7-6-4"], 5360)

    def test_parse_result_html(self):
        doc = parse_result_html(SAMPLE_HTML)
        assert doc is not None
        self.assertEqual(doc["winner_horse_number"], 7)
        self.assertTrue(doc["finalized"])

    def test_unfinalized(self):
        self.assertIsNone(parse_result_html("<html>no table</html>"))

    def test_pi_payload_to_bundle(self):
        from app.ops.netkeiba_results import pi_payload_to_bundle

        payload = {
            "race_id": "2026-07-26-01-01",
            "race_date": "2026-07-26",
            "venue": "新潟",
            "race_number": 1,
            "prediction_available": True,
            "prediction": {
                "candidates": [
                    {"CandidateID": "A", "Rank": 1, "HorseNumber": 7, "Confidence": 0.2},
                    {"CandidateID": "B", "Rank": 2, "HorseNumber": 3, "Confidence": 0.1},
                ]
            },
        }
        bundle = pi_payload_to_bundle(payload)
        assert bundle is not None
        runners = bundle["evaluation"]["runners"]
        self.assertEqual(runners[0]["horse_number"], 7)
        self.assertEqual(runners[0]["mark"], "honmei")
        self.assertEqual(runners[1]["mark"], "taikou")


if __name__ == "__main__":
    unittest.main()
