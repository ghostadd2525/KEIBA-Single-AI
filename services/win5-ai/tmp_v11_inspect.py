from app.data.db import connect
from pathlib import Path

conn = connect()
print("race_evaluations", conn.execute("SELECT COUNT(*) FROM race_evaluations").fetchone()[0])
print(
    "eval sample",
    [
        dict(x)
        for x in conn.execute(
            "SELECT race_id, race_date, venue, hit_at_1, engine_source FROM race_evaluations ORDER BY id DESC LIMIT 3"
        ).fetchall()
    ],
)
print("races count", conn.execute("SELECT COUNT(*) FROM races").fetchone()[0])
print(
    "races with class",
    conn.execute(
        "SELECT COUNT(*) FROM races WHERE class_label IS NOT NULL AND class_label!=''"
    ).fetchone()[0],
)
print(
    "youngish",
    conn.execute(
        "SELECT COUNT(*) FROM races WHERE class_label LIKE '%2歳%' OR class_label LIKE '%3歳未勝利%' OR class_label LIKE '%新馬%'"
    ).fetchone()[0],
)
print(
    "class samples",
    [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT class_label FROM races WHERE class_label IS NOT NULL LIMIT 40"
        ).fetchall()
    ],
)
print("archives", sorted(p.name for p in Path("var/race-archives").glob("*"))[:40])
print("snapshots dirs", sorted(p.name for p in Path("../../evidence/research/prediction-snapshots").glob("*"))[:40] if Path("../../evidence/research/prediction-snapshots").exists() else "missing")
