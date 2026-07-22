# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pi_keibanet.netkeiba.client import NetkeibaClient
from pi_keibanet.netkeiba.parse import parse_entries_from_shutuba
from pi_keibanet.venues import COURSE_CODE_TO_NAME

client = NetkeibaClient(min_interval_sec=0)
OUT = ROOT / "var" / "debug"
OUT.mkdir(parents=True, exist_ok=True)

# mobile list
html = client.fetch("https://race.sp.netkeiba.com/?pid=race_list&kaisai_date=20260725")
(OUT / "sp_race_list_20260725.html").write_text(html, encoding="utf-8")
ids = list(dict.fromkeys(re.findall(r"race_id=(\d{12})", html)))
print("sp ids", len(ids))
for rid in ids:
    print(COURSE_CODE_TO_NAME.get(rid[4:6], rid[4:6]), int(rid[-2:]), rid)

for rid in ["202604020101", "202604020106", "202607020101", "202601010101", "202601010110"]:
    shutuba = client.fetch_shutuba(rid)
    (OUT / f"shutuba_{rid}.html").write_text(shutuba, encoding="utf-8")
    entries = parse_entries_from_shutuba(shutuba)
    print(rid, "entries", len(entries), "title snippet:", shutuba[shutuba.find("RaceName"):shutuba.find("RaceName")+200] if "RaceName" in shutuba else shutuba[:120])
