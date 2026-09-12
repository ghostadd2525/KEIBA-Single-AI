#!/usr/bin/env python3
"""Extract the stdout tar/base64 payload on Windows or the review machine.

Never run this on Production. It writes only to the destination you pass.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import re
import sys
import tarfile
from pathlib import Path

CAPTURE_RELS = (
    "app/main.py",
    "app/data/repository/__init__.py",
    "app/core/feature_loader_bridge.py",
)
BEGIN = "=== TAR_BASE64_BEGIN ==="
END = "=== TAR_BASE64_END ==="
REL_RE = re.compile(r"^CAPTURE_REL=(.+)$")
PATH_RE = re.compile(r"^CAPTURE_PATH=(.+)$")
SIZE_RE = re.compile(r"^CAPTURE_SIZE=(.+)$")
SHA_RE = re.compile(r"^CAPTURE_SHA256=([0-9a-f]{64}|ABSENT|UNREADABLE)$")


def out(msg: str) -> None:
    print(msg)


def parse_records(text: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        m = REL_RE.match(line)
        if m:
            current = {"rel": m.group(1)}
            records.append(current)
            continue
        if current is None:
            continue
        m = PATH_RE.match(line)
        if m:
            current["path"] = m.group(1)
            continue
        m = SIZE_RE.match(line)
        if m:
            current["size"] = m.group(1)
            continue
        m = SHA_RE.match(line)
        if m:
            current["sha256"] = m.group(1)
            continue
    return [r for r in records if r.get("rel") in CAPTURE_RELS]


def extract_b64(text: str) -> str:
    start = text.find(BEGIN)
    end = text.find(END)
    if start < 0 or end < 0 or end <= start:
        raise SystemExit("transcript has no TAR_BASE64 block")
    body = text[start + len(BEGIN) : end]
    return "".join(body.split())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract live-source capture on Windows/review only")
    parser.add_argument("transcript", help="Owner stdout transcript saved on Windows")
    parser.add_argument("--out", required=True, help="Windows/review destination directory")
    args = parser.parse_args(argv)
    src = Path(args.transcript)
    dest = Path(args.out)
    if not src.is_file():
        raise SystemExit("transcript not found: %s" % src)
    dest.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8", errors="replace")
    if "CAPTURE_RESULT=GO" not in text:
        raise SystemExit("transcript CAPTURE_RESULT is not GO")
    records = parse_records(text)
    b64 = extract_b64(text)
    blob = base64.b64decode(b64, validate=True)
    members: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        names = [m.name for m in tar.getmembers() if m.isfile()]
        if sorted(names) != sorted(CAPTURE_RELS):
            raise SystemExit("tar members != capture rels: %s" % names)
        for name in CAPTURE_RELS:
            extracted = tar.extractfile(name)
            if extracted is None:
                raise SystemExit("missing tar member: %s" % name)
            members[name] = extracted.read()
    manifest = [
        "PACK=production_disabled_post_live_source_capture_readonly_20260912",
        "KIND=WINDOWS_OR_REVIEW_EXTRACT",
        "PRODUCTION_WRITE=NO",
        "SCP_UPLOAD=NO",
    ]
    by_rel = {r["rel"]: r for r in records}
    for rel in CAPTURE_RELS:
        data = members[rel]
        digest = hashlib.sha256(data).hexdigest()
        rec = by_rel.get(rel, {})
        if rec.get("sha256") and rec["sha256"] != digest:
            raise SystemExit("extracted sha mismatch %s transcript=%s file=%s" % (rel, rec["sha256"], digest))
        if rec.get("size") and rec["size"].isdigit() and int(rec["size"]) != len(data):
            raise SystemExit("extracted size mismatch %s" % rel)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        out("WROTE %s size=%s sha256=%s" % (rel, len(data), digest))
        manifest.append("REL=%s" % rel)
        manifest.append("LIVE_PATH=%s" % rec.get("path", "UNKNOWN"))
        manifest.append("SIZE=%s" % len(data))
        manifest.append("SHA256=%s" % digest)
    (dest / "MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    out("EXTRACT_RESULT=GO")
    out("DEST=%s" % dest)
    out("PRODUCTION_CODE_DEPLOY_ALLOWED=NO")
    out("DEPLOY_EXECUTION_PACK=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
