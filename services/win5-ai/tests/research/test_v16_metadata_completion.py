# -*- coding: utf-8 -*-
"""V16 Metadata Completion unit tests."""
from __future__ import annotations

import unittest

from app.research.metadata_completion import (
    _norm_going,
    _norm_surface,
    parse_netkeiba_race_meta_html,
)


class MetadataCompletionHelpers(unittest.TestCase):
    def test_norm_surface_going(self):
        self.assertEqual(_norm_surface("turf"), "芝")
        self.assertEqual(_norm_surface("ダート"), "ダート")
        self.assertEqual(_norm_going("稍重"), "稍重")

    def test_parse_html_meta(self):
        html = """
        <div class="Diary_Snap_RaceData01">天候:晴 馬場:良 芝1600m 出走16頭</div>
        """
        parsed = parse_netkeiba_race_meta_html(html)
        self.assertEqual(parsed.get("surface"), "芝")
        self.assertEqual(parsed.get("distance"), 1600)
        self.assertEqual(parsed.get("weather"), "晴")
        self.assertEqual(parsed.get("going"), "良")
        self.assertEqual(parsed.get("field_size"), 16)


if __name__ == "__main__":
    unittest.main()
