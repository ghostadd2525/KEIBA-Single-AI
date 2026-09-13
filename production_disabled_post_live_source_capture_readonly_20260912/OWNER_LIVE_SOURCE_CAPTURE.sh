#!/usr/bin/env bash
# Read-only Production live-source capture. Paste on the Production SSH host.
# Do not copy files onto Production. Do not redirect this script to a file
# on the Production host. Stdout only. Windows saves the transcript.
# Forbids: write, restart, env change, migrate, POST, deploy, APPLY, SCP.
# Canonical file: OWNER_LIVE_SOURCE_CAPTURE.sh
# Presented file: OWNER_PASTE_COMMAND_BLOCK.sh
# These two files are generated as byte-identical copies.
set -u
export LC_ALL=C

echo "===== BEGIN OWNER_READ_ONLY_LIVE_SOURCE_CAPTURE ====="
echo "PACK=production_disabled_post_live_source_capture_readonly_20260912"
echo "LIVE_COMPARE_V5_GO_IS_NOT_DEPLOY_APPROVAL=YES"
echo "OWNER_LOG_SHA256=4a65fd2ca5f54284268975d90d28e65222c785421b204567bb3bf1780be28c94"
echo "PRODUCTION_CODE_DEPLOY_ALLOWED=NO"
echo "OWNER_DEPLOY_APPROVED=NO"
echo "POST_CODE_PRODUCTION_DEPLOYED=NO"
echo "OWNER_EXECUTE_NOW=NO"
echo "CURSOR_PRODUCTION_SSH=NO"
echo "THIS_SCRIPT_WRITES=NO"
echo "SCP_UPLOAD=NO"
echo "ENV_DUMP=NO"
echo "SQLITE=NO"
echo "RACE_ID_COLLECT=NO"
echo "DEPLOY_EXECUTION_PACK=NO"
echo "HOST=$(hostname 2>/dev/null || echo UNKNOWN)"
echo "WHEN_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo UNKNOWN)"

python3 - <<'PY'
#!/usr/bin/env python3
"""Read-only Production live-source capture. Stdout only. No writes.

Opens exactly three files read-only, prints path/size/SHA256, and
emits an in-memory tar.gz as base64. Does not dump env, sqlite,
race_id, or secrets. Does not write on the host.
"""
from __future__ import annotations

import base64
import hashlib
import io
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path

UNIT = "expect-ai.service"
CAPTURE_RELS = (
    "app/main.py",
    "app/data/repository/__init__.py",
    "app/core/feature_loader_bridge.py",
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SECRET_FORM_RE = re.compile(
    r"(?i)(?:[a-z][a-z0-9+.-]*://|bearer\b|userinfo|[/:][^/\s]+:[^/\s]+@)"
)
SAFE_EXEC_NAME_RE = re.compile(r"^[A-Za-z0-9._+-]+$")

stops: list[str] = []
notes: list[str] = []


def out(msg: str) -> None:
    print(msg, flush=True)


def sh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def looks_secret_form(tok: str) -> bool:
    if not tok:
        return False
    if "://" in tok:
        return True
    if SECRET_FORM_RE.search(tok):
        return True
    if "=" in tok:
        return True
    return False


def safe_exec_path(path: str) -> str:
    if not path:
        return ""
    if looks_secret_form(path):
        return ""
    if path.startswith("/") and ".." not in path.split("/"):
        return path
    if SAFE_EXEC_NAME_RE.match(path):
        return path
    return ""


def execstart_path_only(blob: str) -> str:
    raw_path = ""
    m = re.search(r"path=([^ ;]+)", blob)
    if m:
        raw_path = m.group(1)
    return safe_exec_path(raw_path)


def systemd_show(unit: str) -> dict[str, str]:
    """Read-only unit metadata. Never requests Environment*."""
    proc = sh(
        "systemctl",
        "show",
        unit,
        "-p",
        "Id",
        "-p",
        "FragmentPath",
        "-p",
        "WorkingDirectory",
        "-p",
        "ExecStart",
        "-p",
        "LoadState",
    )
    parsed: dict[str, str] = {}
    if proc.returncode != 0:
        parsed["_error"] = (proc.stderr or proc.stdout or "systemctl_show_failed").strip()
        return parsed
    for line in (proc.stdout or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            parsed[k] = v
    return parsed


def discover_win5(show: dict[str, str]) -> Path | None:
    cands: list[Path] = []
    wd = (show.get("WorkingDirectory") or "").strip()
    if wd:
        cands.append(Path(wd))
        cands.append(Path(wd) / "services" / "win5-ai")
    safe_path = execstart_path_only(show.get("ExecStart") or "")
    if safe_path:
        p = Path(safe_path)
        if p.suffix == ".py" or p.name == "run.py":
            cands.append(p.parent)
            cands.append(p.parent / "services" / "win5-ai")
        if p.is_dir():
            cands.append(p)
    cands.extend(
        [
            Path("/home/ubuntu/KEIBA-Single-AI/services/win5-ai"),
            Path("/home/ubuntu/KEIBA-Single-AI"),
            Path("/opt/expect-ai/current/services/win5-ai"),
            Path("/opt/expect-ai/services/win5-ai"),
        ]
    )
    seen: set[Path] = set()
    for cand in cands:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "app" / "main.py").is_file():
            return resolved
        if (resolved / "services" / "win5-ai" / "app" / "main.py").is_file():
            return resolved / "services" / "win5-ai"
    return None


def read_readonly(path: Path) -> bytes:
    fd = os.open(os.fspath(path), os.O_RDONLY)
    with os.fdopen(fd, "rb") as fh:
        return fh.read()


def make_tar_gz(members: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.USTAR_FORMAT, compresslevel=9) as tar:
        for name, data in members:
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def emit_base64(blob: bytes) -> None:
    b64 = base64.b64encode(blob).decode("ascii")
    out("TAR_B64_CHARS=%s" % len(b64))
    out("TAR_B64_SHA256=%s" % sha256_bytes(b64.encode("ascii")))
    out("=== TAR_BASE64_BEGIN ===")
    for i in range(0, len(b64), 76):
        out(b64[i : i + 76])
    out("=== TAR_BASE64_END ===")


def reset_state() -> None:
    stops.clear()
    notes.clear()


def emit_judgment(captured: int) -> str:
    result = "GO" if not stops and captured == len(CAPTURE_RELS) else "STOP"
    out("----- judgment -----")
    out("CAPTURE_RESULT=%s" % result)
    out("CAPTURED_FILE_COUNT=%s" % captured)
    out("CAPTURE_REL_COUNT=%s" % len(CAPTURE_RELS))
    out("PRODUCTION_CODE_DEPLOY_ALLOWED=NO")
    out("OWNER_DEPLOY_APPROVED=NO")
    out("POST_CODE_PRODUCTION_DEPLOYED=NO")
    out("LIVE_COMPARE_V5_GO_IS_NOT_DEPLOY_APPROVAL=YES")
    out("DEPLOY_EXECUTION_PACK=NO")
    out("WHOLESALE_REPLACE=NO")
    if stops:
        for s in stops:
            out("STOP_REASON=%s" % s)
    if notes:
        for n in notes:
            out("NOTE=%s" % n)
    if result == "GO":
        out("NEXT_FOR_OWNER=save this stdout on Windows only; return transcript + extracted files")
    else:
        out("NEXT_FOR_OWNER=return this stdout; do not write on Production; do not deploy")
    out("NEXT_STEP=INDEPENDENT_REVIEW_OF_READONLY_LIVE_SOURCE_CAPTURE_PACK")
    return result


def main() -> int:
    reset_state()
    out("PACK=production_disabled_post_live_source_capture_readonly_20260912")
    out("KIND=OWNER_READ_ONLY_LIVE_SOURCE_CAPTURE")
    out("CURSOR_PRODUCTION_SSH=NO")
    out("THIS_SCRIPT_WRITES=NO")
    out("SCP_UPLOAD=NO")
    out("ENV_DUMP=NO")
    out("SQLITE=NO")
    out("RACE_ID_COLLECT=NO")
    out("CAPTURE_REL_COUNT=%s" % len(CAPTURE_RELS))
    for rel in CAPTURE_RELS:
        out("CAPTURE_TARGET=%s" % rel)

    out("----- systemd -----")
    show = systemd_show(UNIT)
    if "_error" in show:
        out("SYSTEMD_SHOW=FAIL")
        notes.append("systemd_show_failed_fallback_paths_tried")
    else:
        out("SYSTEMD_SHOW=OK")
        out("SYSTEMD_UNIT=%s" % (show.get("Id") or UNIT))
        load_state = (show.get("LoadState") or "").strip()
        out("SYSTEMD_LOADSTATE=%s" % (load_state or "ABSENT"))
        wd = (show.get("WorkingDirectory") or "").strip()
        out("SYSTEMD_WORKINGDIRECTORY=%s" % (wd or "ABSENT"))
        # ExecStart is used only to discover the win5 root. Never printed.

    out("----- paths -----")
    win5 = discover_win5(show if "_error" not in show else {})
    out("WIN5_ROOT=%s" % (win5 if win5 else "ABSENT"))
    if win5 is None:
        stops.append("win5_root_not_found")
        emit_judgment(0)
        return 2

    members: list[tuple[str, bytes]] = []
    out("----- files -----")
    for rel in CAPTURE_RELS:
        path = win5 / rel
        out("CAPTURE_REL=%s" % rel)
        if not path.is_file():
            out("CAPTURE_PATH=ABSENT")
            out("CAPTURE_SIZE=ABSENT")
            out("CAPTURE_SHA256=ABSENT")
            out("CAPTURE_OPEN=ABSENT")
            stops.append("capture_file_absent:%s" % rel)
            continue
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        out("CAPTURE_PATH=%s" % resolved)
        try:
            data = read_readonly(path)
        except OSError:
            out("CAPTURE_SIZE=UNREADABLE")
            out("CAPTURE_SHA256=UNREADABLE")
            out("CAPTURE_OPEN=FAIL")
            stops.append("capture_file_unreadable:%s" % rel)
            continue
        digest = sha256_bytes(data)
        if not HEX64.match(digest):
            stops.append("capture_hash_invalid:%s" % rel)
        out("CAPTURE_SIZE=%s" % len(data))
        out("CAPTURE_SHA256=%s" % digest)
        out("CAPTURE_OPEN=OK")
        members.append((rel, data))

    out("----- payload -----")
    if len(members) != len(CAPTURE_RELS) or stops:
        out("TAR_MEMBER_COUNT=0")
        out("TAR_PAYLOAD=OMITTED_INCOMPLETE")
        emit_judgment(len(members))
        return 2

    blob = make_tar_gz(members)
    out("TAR_MEMBER_COUNT=%s" % len(members))
    out("TAR_GZ_BYTES=%s" % len(blob))
    out("TAR_GZ_SHA256=%s" % sha256_bytes(blob))
    for rel, data in members:
        out("TAR_MEMBER=%s size=%s sha256=%s" % (rel, len(data), sha256_bytes(data)))
    emit_base64(blob)
    result = emit_judgment(len(members))
    return 0 if result == "GO" else 2


if __name__ == "__main__":
    sys.exit(main())

PY

rc=$?
echo "===== END OWNER_READ_ONLY_LIVE_SOURCE_CAPTURE ====="
exit "$rc"
