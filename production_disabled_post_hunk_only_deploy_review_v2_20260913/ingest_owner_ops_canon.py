#!/usr/bin/env python3
"""Copy Owner-returned live ops files into live_canon after SHA checks.

Does not invent bytes. Does not deploy. Does not talk to Production.
Rejects capture-tool fixtures. Does not rewrite SHA256SUMS.txt.
"""
from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

PACK = Path(__file__).resolve().parent
CAPACITY_NAME = "prediction_capacity.py"
STORE_NAME = "final_prediction_store.py"
CAPACITY_SHA = "c351bd9753d20994156e00141d564a55a42891983ecab5b2c5c55a32d9908f1e"
STORE_SHA = "40352ff56b3267533267d5de9c893f3bda8963d5fe121474f7785b0152594a12"
CAPACITY_SIZE = 15241
STORE_SIZE = 22775
FIXTURE_MARK = "CAPTURE_TOOL_FIXTURE"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reject_fixture(data: bytes, label: str) -> None:
    if FIXTURE_MARK.encode("utf-8") in data:
        raise SystemExit("fixture_rejected:%s" % label)


def read_named_from_zip(zip_path: Path, filename: str) -> bytes:
    with zipfile.ZipFile(zip_path) as zf:
        matches = [n for n in zf.namelist() if n.rstrip("/").endswith("/" + filename) or n == filename]
        if len(matches) != 1:
            raise SystemExit("zip_member_count:%s:%s:%s" % (zip_path, filename, len(matches)))
        data = zf.read(matches[0])
    return data


def load_file(path: Path, filename: str, expect_sha: str, expect_size: int) -> bytes:
    if path.suffix.lower() == ".zip":
        data = read_named_from_zip(path, filename)
    else:
        data = path.read_bytes()
    reject_fixture(data, filename)
    if len(data) != expect_size:
        raise SystemExit("size_mismatch:%s:%s" % (filename, len(data)))
    digest = sha256_bytes(data)
    if digest != expect_sha:
        raise SystemExit("sha_mismatch:%s:%s" % (filename, digest))
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest Owner live ops canon")
    parser.add_argument("--capacity-zip", default="")
    parser.add_argument("--store-zip", default="")
    parser.add_argument("--capacity-file", default="")
    parser.add_argument("--store-file", default="")
    args = parser.parse_args(argv)

    cap_src = args.capacity_file or args.capacity_zip
    store_src = args.store_file or args.store_zip
    if not cap_src or not store_src:
        print("USAGE=provide capacity and store zip or file")
        print("LIVE_OPS_PRESENT=NO")
        return 2

    cap = load_file(Path(cap_src), CAPACITY_NAME, CAPACITY_SHA, CAPACITY_SIZE)
    store = load_file(Path(store_src), STORE_NAME, STORE_SHA, STORE_SIZE)

    dest = PACK / "live_canon/app/ops"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / CAPACITY_NAME).write_bytes(cap)
    (dest / STORE_NAME).write_bytes(store)
    marker = dest / "LIVE_BYTES_REQUIRED.txt"
    if marker.exists():
        marker.unlink()

    print("INGEST_CAPACITY_SHA256=%s" % CAPACITY_SHA)
    print("INGEST_STORE_SHA256=%s" % STORE_SHA)
    print("DEPLOY_CANDIDATE=NO")
    print("LIVE_OPS_PRESENT=YES")
    print("SHA256SUMS_NOT_REWRITTEN=YES")
    print("NEXT=python3 generate_sha256sums.py && python3 run_tests.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
