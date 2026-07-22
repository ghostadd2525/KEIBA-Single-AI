#!/usr/bin/env python3
import json
import os
import sqlite3
import sys

sys.path.insert(0, "/home/ubuntu/KEIBA-Single-AI/services/win5-ai")
os.chdir("/home/ubuntu/KEIBA-Single-AI/services/win5-ai")

db = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db"
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

print("=== job status counts ===")
for row in conn.execute(
    "SELECT status, COUNT(*) AS n FROM collect_jobs WHERE week_id=? GROUP BY status",
    ("2026-07-25",),
):
    print(dict(row))

print("=== pending scheduled_for ===")
for row in conn.execute(
    "SELECT job_id, kind, scheduled_for, status FROM collect_jobs WHERE week_id=? AND status='PENDING' ORDER BY scheduled_for LIMIT 5",
    ("2026-07-25",),
):
    print(dict(row))

row = conn.execute(
    "SELECT job_id FROM collect_jobs WHERE week_id=? AND status='PENDING' AND scheduled_for <= '2026-07-21' ORDER BY scheduled_for LIMIT 1",
    ("2026-07-25",),
).fetchone()
if not row:
    row = conn.execute(
        "SELECT job_id FROM collect_jobs WHERE week_id=? AND status='FAILED' ORDER BY job_id LIMIT 1",
        ("2026-07-25",),
    ).fetchone()
    if row:
        conn.execute("UPDATE collect_jobs SET status='PENDING', attempt=0 WHERE job_id=?", (row["job_id"],))
        conn.commit()
        print("requeued failed job", row["job_id"])

if not row:
    print("no job found")
    sys.exit(1)

from app.data.collect import KeibaNetCollector
from app.data.collect.keibanet.client import KeibaNetClient
from app.data.db import migrate

migrate()
base = os.environ.get("EXPECT_KEIBANET_BASE_URL", "http://127.0.0.1:8081")
client = KeibaNetClient(base_url=base)
collector = KeibaNetCollector(client=client)

job_id = row["job_id"]
print("=== run_job", job_id, "base=", base, "===")
result = collector.run_job(job_id)
print(json.dumps(result.__dict__ if hasattr(result, "__dict__") else result, ensure_ascii=False, indent=2, default=str))

from app.data.etl.from_raw import ingest_ready_entries_core, ingest_ready_race_meta

print("=== etl race_meta ===", ingest_ready_race_meta("2026-07-25").as_dict())
print("=== etl entries_core ===", ingest_ready_entries_core("2026-07-25").as_dict())
