#!/usr/bin/env python3
"""Extract the stdout tar/base64 payload on Windows or the review machine.

Never run this on Production. Writes only after every transcript, tar,
and byte check passes. On any failure: EXTRACT_RESULT=STOP and zero files.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import io
import re
import shutil
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
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RESULT_RE = re.compile(r"(?m)^CAPTURE_RESULT=(.*)$")
REL_RE = re.compile(r"(?m)^CAPTURE_REL=(.*)$")
SIZE_RE = re.compile(r"(?m)^CAPTURE_SIZE=(.*)$")
SHA_RE = re.compile(r"(?m)^CAPTURE_SHA256=(.*)$")
PATH_RE = re.compile(r"(?m)^CAPTURE_PATH=(.*)$")
MEMBER_RE = re.compile(
    r"(?m)^TAR_MEMBER=(\S+) size=(\d+) sha256=([0-9a-f]{64})$"
)
B64_CHARS_RE = re.compile(r"(?m)^TAR_B64_CHARS=(\d+)$")
B64_SHA_RE = re.compile(r"(?m)^TAR_B64_SHA256=([0-9a-f]{64})$")
GZ_BYTES_RE = re.compile(r"(?m)^TAR_GZ_BYTES=(\d+)$")
GZ_SHA_RE = re.compile(r"(?m)^TAR_GZ_SHA256=([0-9a-f]{64})$")
PACK_NAME = "production_disabled_post_live_source_capture_readonly_v3_20260912"


class ExtractError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def out(msg: str) -> None:
    print(msg)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_one(matches: list[str], label: str) -> str:
    if len(matches) != 1:
        raise ExtractError("%s_count=%s" % (label, len(matches)))
    return matches[0]


def split_payload(text: str) -> tuple[str, str]:
    begin_n = text.count(BEGIN)
    end_n = text.count(END)
    if begin_n != 1 or end_n != 1:
        raise ExtractError("marker_count_begin=%s_end=%s" % (begin_n, end_n))
    start = text.find(BEGIN)
    end = text.find(END)
    if start < 0 or end < 0 or end <= start:
        raise ExtractError("marker_order")
    prefix = text[:start]
    body = text[start + len(BEGIN) : end]
    suffix = text[end + len(END) :]
    metadata = prefix + suffix
    b64 = "".join(body.split())
    if not b64:
        raise ExtractError("empty_base64")
    return metadata, b64


def parse_result(metadata: str) -> None:
    results = RESULT_RE.findall(metadata)
    if results.count("STOP") and results.count("GO"):
        raise ExtractError("capture_result_mixed")
    if results != ["GO"]:
        raise ExtractError("capture_result_not_single_go")


def parse_kv_block(metadata: str) -> list[dict[str, str]]:
    """Parse sequential CAPTURE_REL records from metadata only."""
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in metadata.splitlines():
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
    return records


def parse_records(metadata: str) -> list[dict[str, str]]:
    records = parse_kv_block(metadata)
    rels = [r.get("rel", "") for r in records]
    if len(rels) != len(CAPTURE_RELS):
        raise ExtractError("capture_rel_count=%s" % len(rels))
    if rels != list(CAPTURE_RELS):
        if len(set(rels)) != len(rels):
            raise ExtractError("capture_rel_duplicate")
        extra = [r for r in rels if r not in CAPTURE_RELS]
        missing = [r for r in CAPTURE_RELS if r not in rels]
        if extra:
            raise ExtractError("capture_rel_extra")
        if missing:
            raise ExtractError("capture_rel_missing")
        raise ExtractError("capture_rel_mismatch")
    for rec in records:
        size = rec.get("size")
        digest = rec.get("sha256")
        if size is None or digest is None:
            raise ExtractError("capture_record_incomplete:%s" % rec["rel"])
        if not size.isdigit():
            raise ExtractError("capture_size_missing:%s" % rec["rel"])
        if not HEX64.match(digest):
            raise ExtractError("capture_sha_missing:%s" % rec["rel"])
    return records


def parse_members(metadata: str) -> list[tuple[str, int, str]]:
    found = MEMBER_RE.findall(metadata)
    if len(found) != len(CAPTURE_RELS):
        raise ExtractError("tar_member_record_count=%s" % len(found))
    names = [n for n, _s, _h in found]
    if names != list(CAPTURE_RELS):
        if len(set(names)) != len(names):
            raise ExtractError("tar_member_record_duplicate")
        extra = [n for n in names if n not in CAPTURE_RELS]
        if extra:
            raise ExtractError("tar_member_record_extra")
        raise ExtractError("tar_member_record_mismatch")
    return [(n, int(s), h) for n, s, h in found]


def parse_one_int(metadata: str, cre: re.Pattern[str], label: str) -> int:
    return int(require_one(cre.findall(metadata), label))


def parse_one_sha(metadata: str, cre: re.Pattern[str], label: str) -> str:
    digest = require_one(cre.findall(metadata), label)
    if not HEX64.match(digest):
        raise ExtractError("%s_not_hex64" % label)
    return digest


def unsafe_member_name(name: str) -> str | None:
    if not name:
        return "empty_name"
    if name.startswith("/") or name.startswith("\\"):
        return "absolute_member"
    if ":" in name and name.split(":", 1)[0].isalpha() and len(name.split(":", 1)[0]) == 1:
        return "absolute_member"
    parts = name.replace("\\", "/").split("/")
    if any(p == ".." for p in parts):
        return "dotdot_member"
    return None


def read_tar_members(blob: bytes) -> dict[str, bytes]:
    try:
        tar = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise ExtractError("tar_open_failed:%s" % type(exc).__name__) from exc
    with tar:
        infos = tar.getmembers()
        if len(infos) != len(CAPTURE_RELS):
            raise ExtractError("tar_member_count=%s" % len(infos))
        names = [info.name for info in infos]
        if len(set(names)) != len(names):
            raise ExtractError("tar_member_duplicate")
        members: dict[str, bytes] = {}
        for info in infos:
            bad = unsafe_member_name(info.name)
            if bad:
                raise ExtractError(bad)
            if info.issym():
                raise ExtractError("symlink_member")
            if info.islnk():
                raise ExtractError("hardlink_member")
            if not info.isreg() or info.type != tarfile.REGTYPE:
                raise ExtractError("member_type_not_regfile")
            extracted = tar.extractfile(info)
            if extracted is None:
                raise ExtractError("tar_extractfile_none:%s" % info.name)
            data = extracted.read()
            if info.size != len(data):
                raise ExtractError("tar_member_size_mismatch:%s" % info.name)
            members[info.name] = data
        if names != list(CAPTURE_RELS):
            extra = [n for n in names if n not in CAPTURE_RELS]
            if extra:
                raise ExtractError("tar_member_extra")
            raise ExtractError("tar_member_name_mismatch")
    return members


def cross_check(
    records: list[dict[str, str]],
    member_recs: list[tuple[str, int, str]],
    members: dict[str, bytes],
) -> None:
    rec_by = {r["rel"]: r for r in records}
    mem_by = {n: (sz, digest) for n, sz, digest in member_recs}
    for rel in CAPTURE_RELS:
        data = members[rel]
        rec = rec_by[rel]
        rec_size = int(rec["size"])
        rec_sha = rec["sha256"]
        mem_size, mem_sha = mem_by[rel]
        data_sha = sha256_bytes(data)
        data_size = len(data)
        if not (rec_size == mem_size == data_size):
            raise ExtractError("size_mismatch:%s" % rel)
        if not (rec_sha == mem_sha == data_sha):
            raise ExtractError("sha_mismatch:%s" % rel)


def write_outputs(dest: Path, records: list[dict[str, str]], members: dict[str, bytes]) -> None:
    dest.mkdir(parents=True, exist_ok=False)
    try:
        rec_by = {r["rel"]: r for r in records}
        manifest = [
            "PACK=%s" % PACK_NAME,
            "KIND=WINDOWS_OR_REVIEW_EXTRACT",
            "PRODUCTION_WRITE=NO",
            "SCP_UPLOAD=NO",
        ]
        for rel in CAPTURE_RELS:
            data = members[rel]
            digest = sha256_bytes(data)
            target = dest / rel
            if target.exists() or ".." in Path(rel).parts:
                raise ExtractError("unsafe_output_path:%s" % rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            out("WROTE %s size=%s sha256=%s" % (rel, len(data), digest))
            rec = rec_by[rel]
            manifest.append("REL=%s" % rel)
            manifest.append("LIVE_PATH=%s" % rec.get("path", "UNKNOWN"))
            manifest.append("SIZE=%s" % len(data))
            manifest.append("SHA256=%s" % digest)
        (dest / "MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise


def extract(transcript: Path, dest: Path) -> None:
    if dest.exists():
        raise ExtractError("out_dir_exists")
    if not transcript.is_file():
        raise ExtractError("transcript_absent")
    text = transcript.read_text(encoding="utf-8", errors="replace")
    metadata, b64 = split_payload(text)
    parse_result(metadata)
    records = parse_records(metadata)
    member_recs = parse_members(metadata)
    b64_chars = parse_one_int(metadata, B64_CHARS_RE, "tar_b64_chars")
    b64_sha = parse_one_sha(metadata, B64_SHA_RE, "tar_b64_sha256")
    gz_bytes = parse_one_int(metadata, GZ_BYTES_RE, "tar_gz_bytes")
    gz_sha = parse_one_sha(metadata, GZ_SHA_RE, "tar_gz_sha256")
    if len(b64) != b64_chars:
        raise ExtractError("tar_b64_chars_mismatch")
    if sha256_bytes(b64.encode("ascii")) != b64_sha:
        raise ExtractError("tar_b64_sha256_mismatch")
    try:
        blob = base64.b64decode(b64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ExtractError("base64_decode_failed") from exc
    if len(blob) != gz_bytes:
        raise ExtractError("tar_gz_bytes_mismatch")
    if sha256_bytes(blob) != gz_sha:
        raise ExtractError("tar_gz_sha256_mismatch")
    members = read_tar_members(blob)
    cross_check(records, member_recs, members)
    write_outputs(dest, records, members)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract live-source capture on Windows/review only")
    parser.add_argument("transcript", help="Owner stdout transcript saved on Windows")
    parser.add_argument("--out", required=True, help="Windows/review destination directory")
    args = parser.parse_args(argv)
    dest = Path(args.out)
    try:
        extract(Path(args.transcript), dest)
    except ExtractError as exc:
        if dest.exists():
            # Must not leave a partial extract. Fail closed if anything appeared.
            out("EXTRACT_RESULT=STOP")
            out("STOP_REASON=%s" % exc.reason)
            out("EXTRACTED_FILE_COUNT=UNKNOWN_DEST_ALREADY_PRESENT")
            out("PRODUCTION_CODE_DEPLOY_ALLOWED=NO")
            out("DEPLOY_EXECUTION_PACK=NO")
            return 2
        out("EXTRACT_RESULT=STOP")
        out("STOP_REASON=%s" % exc.reason)
        out("EXTRACTED_FILE_COUNT=0")
        out("PRODUCTION_CODE_DEPLOY_ALLOWED=NO")
        out("DEPLOY_EXECUTION_PACK=NO")
        return 2
    out("EXTRACT_RESULT=GO")
    out("DEST=%s" % dest)
    out("EXTRACTED_FILE_COUNT=3")
    out("PRODUCTION_CODE_DEPLOY_ALLOWED=NO")
    out("DEPLOY_EXECUTION_PACK=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
