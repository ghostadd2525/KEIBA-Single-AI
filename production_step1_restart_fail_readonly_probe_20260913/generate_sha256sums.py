"""Write SHA256SUMS.txt last. Do not list SHA256SUMS.txt itself."""
from __future__ import annotations

import hashlib
from pathlib import Path

PACK = Path(__file__).resolve().parent


def write_sha256sums() -> Path:
    lines: list[str] = []
    for path in sorted(PACK.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "SHA256SUMS.txt":
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rel = path.relative_to(PACK).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append("%s  %s" % (digest, rel))
    dest = PACK / "SHA256SUMS.txt"
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def main() -> int:
    dest = write_sha256sums()
    print("WROTE=%s" % dest)
    print("COUNT=%s" % sum(1 for _ in dest.read_text(encoding="utf-8").splitlines() if _.strip()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
