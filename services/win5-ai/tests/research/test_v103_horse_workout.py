# -*- coding: utf-8 -*-
"""V10.3 Horse / Workout collector unit tests."""
from __future__ import annotations

import unittest

from app.research.collector.horse_collector import parse_horse_profile, parse_pedigree_ajax
from app.research.collector.workout_collector import parse_oikiri_html


class HorseParseTests(unittest.TestCase):
    def test_profile_th_td(self):
        html = """
        <table>
          <tr><th>調教師</th><td>西園翔太 (栗東)</td></tr>
          <tr><th>馬主</th><td>渡邉直樹</td></tr>
          <tr><th>生産者</th><td>川越ファーム</td></tr>
          <tr><th>セリ取引価格</th><td>-</td></tr>
        </table>
        """
        p = parse_horse_profile(html)
        self.assertEqual(p["owner"], "渡邉直樹")
        self.assertEqual(p["breeder"], "川越ファーム")
        self.assertIsNone(p["sale_price"])

    def test_pedigree_blood_table(self):
        frag = """
        <table class="blood_table">
          <tr>
            <td rowspan="2" class="b_ml"><a href="/horse/ped/1/"><span>エフフォーリア</span></a></td>
            <td class="b_ml"><span>エピファネイア</span></td>
          </tr>
          <tr><td class="b_fml"><span>ケイティーズハート</span></td></tr>
          <tr>
            <td rowspan="2" class="b_fml"><a><span>カラレイア</span></a></td>
            <td class="b_ml"><span>エンパイアメーカー</span></td>
          </tr>
          <tr><td class="b_fml"><span>ベッラレイア</span></td></tr>
        </table>
        """
        ped = parse_pedigree_ajax(frag)
        self.assertEqual(ped["sire"], "エフフォーリア")
        self.assertEqual(ped["damsire"], "エンパイアメーカー")
        self.assertEqual(ped["dam"], "カラレイア")


class OikiriParseTests(unittest.TestCase):
    def test_oikiri_rows(self):
        html = """
        <a href="/horse/2024105886/">ジャストワナフライ</a>
        <tr>
          <td>2026/07/22(水)</td>
          <td>札ダ</td>
          <td>稍</td>
          <td>助手</td>
          <td>- - 59.7 (15.7) 44.0 (31.7) 12.3 (12.3)</td>
          <td>8</td>
          <td>馬也</td>
          <td>仕上十分</td>
          <td>C</td>
        </tr>
        """
        by = parse_oikiri_html(html, horse_ids={"2024105886"})
        self.assertIn("2024105886", by)
        row = by["2024105886"]
        self.assertEqual(row["oikiri_time"], "59.7")
        self.assertEqual(row["oikiri_letter"], "C")


if __name__ == "__main__":
    unittest.main()
