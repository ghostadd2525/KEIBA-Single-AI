#!/usr/bin/env python3
"""Embed candidate tar.gz+base64 into owner_deploy_stdin.py and pin FLAGS SHA."""
from __future__ import annotations

import base64
import hashlib
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STDIN = ROOT / "02_powershell" / "owner_deploy_stdin.py"
CAND = ROOT / "payload" / "candidates"
FLAGS = ROOT / "FLAGS.txt"
BEGIN = "# BEGIN_CANDIDATE_TAR_GZ_B64"
END = "# END_CANDIDATE_TAR_GZ_B64"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_tar_gz() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        base = CAND / "services" / "win5-ai"
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(CAND).as_posix()
            info = tarfile.TarInfo(name=rel)
            data = path.read_bytes()
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def wrap_b64(raw: bytes) -> str:
    token = base64.b64encode(raw).decode("ascii")
    lines = [token[i : i + 76] for i in range(0, len(token), 76)]
    inner = "\n".join('    "%s"' % line for line in lines)
    return "CANDIDATE_TAR_GZ_B64 = (\n%s\n)" % inner


def patch_stdin(blob: str) -> None:
    text = STDIN.read_text(encoding="utf-8")
    start = text.find(BEGIN)
    end = text.find(END)
    if start < 0 or end < 0 or end <= start:
        raise SystemExit("embed markers missing")
    start_line = text.find("\n", start) + 1
    new = text[:start_line] + blob + "\n" + text[end:]
    STDIN.write_text(new, encoding="utf-8")


def patch_flags(payload_sha: str, tar_sha: str) -> None:
    lines = []
    for line in FLAGS.read_text(encoding="utf-8").splitlines():
        if line.startswith("STDIN_PAYLOAD_SHA256="):
            lines.append("STDIN_PAYLOAD_SHA256=" + payload_sha)
        elif line.startswith("CANDIDATE_TAR_GZ_SHA256="):
            lines.append("CANDIDATE_TAR_GZ_SHA256=" + tar_sha)
        else:
            lines.append(line)
    FLAGS.write_text("\n".join(lines) + "\n", encoding="utf-8")


def existing_tar_gz() -> bytes | None:
    text = STDIN.read_text(encoding="utf-8")
    start = text.find(BEGIN)
    end = text.find(END)
    if start < 0 or end <= start:
        return None
    blob = text[start:end]
    if "EMBED_CANDIDATE_TAR_GZ_B64" in blob:
        return None
    parts = []
    for line in blob.splitlines():
        line = line.strip().strip(",")
        if line.startswith('"') and line.endswith('"'):
            parts.append(line[1:-1])
    if not parts:
        return None
    return base64.b64decode("".join(parts).encode("ascii"))


def main() -> int:
    raw = existing_tar_gz()
    if raw is None:
        raw = build_tar_gz()
        patch_stdin(wrap_b64(raw))
    payload_sha = file_sha(STDIN)
    tar_sha = hashlib.sha256(raw).hexdigest()
    patch_flags(payload_sha, tar_sha)
    print("CANDIDATE_TAR_GZ_SHA256=" + tar_sha)
    print("STDIN_PAYLOAD_SHA256=" + payload_sha)
    print("CANDIDATE_TAR_GZ_SIZE=" + str(len(raw)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
