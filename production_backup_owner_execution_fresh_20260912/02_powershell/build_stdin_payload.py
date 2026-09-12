#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build owner_backup_stdin.py at pack-build time. Owner PS1 never concatenates."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "backup_contract.py"
REMOTE = HERE / "owner_backup_remote.py"
STDIN = HERE / "owner_backup_stdin.py"
REVIEWED = "55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e"
FUTURE = "from __future__ import annotations"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strip_embed_header(text: str) -> str:
    tree = ast.parse(text)
    future_end = 0
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            future_end = int(getattr(node, "end_lineno", node.lineno) or node.lineno)
            break
    if future_end <= 0:
        raise SystemExit("future_import_missing_in_source")
    lines = text.splitlines(keepends=True)
    return "".join(lines[future_end:])


def drop_dunder_main(text: str) -> str:
    marker = 'if __name__ == "__main__":'
    idx = text.rfind(marker)
    if idx < 0:
        raise SystemExit("contract __main__ guard missing")
    return text[:idx].rstrip() + "\n"


def build() -> bytes:
    contract_bytes = CONTRACT.read_bytes()
    got = sha256_bytes(contract_bytes)
    if got != REVIEWED:
        raise SystemExit("CONTRACT_SHA_MISMATCH %s" % got)
    contract_body = drop_dunder_main(strip_embed_header(contract_bytes.decode("utf-8")))
    remote_body = strip_embed_header(REMOTE.read_text(encoding="utf-8"))
    leftover = [
        ln
        for ln in (contract_body + remote_body).splitlines()
        if ln.lstrip().startswith(FUTURE)
    ]
    if leftover:
        raise SystemExit("future_import_remained_in_embed_bodies")
    out = (
        "#!/usr/bin/env python3\n"
        "# -*- coding: utf-8 -*-\n"
        '"""Single SSH stdin payload. Pregenerated. Do not concatenate at runtime."""\n'
        "from __future__ import annotations\n"
        "\n"
        "# --- embedded backup_contract.py (shebang/coding/future/__main__ stripped) ---\n"
        + contract_body
        + "\n"
        "# --- embedded owner_backup_remote.py (shebang/coding/future stripped) ---\n"
        + remote_body
    )
    if not out.endswith("\n"):
        out += "\n"
    data = out.encode("utf-8")
    if data.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("bom_forbidden")
    matches = [ln for ln in out.splitlines() if ln.startswith(FUTURE) or ln.lstrip() == FUTURE]
    if len(matches) != 1:
        raise SystemExit("FUTURE_IMPORT_COUNT=%d" % len(matches))
    compile(data, str(STDIN), "exec")
    return data


def main() -> int:
    data = build()
    STDIN.write_bytes(data)
    print("STDIN_PAYLOAD_SHA256=%s" % sha256_bytes(data))
    print("CONTRACT_SHA256=%s" % REVIEWED)
    print("FUTURE_IMPORT_COUNT=1")
    print("STDIN_PATH=%s" % STDIN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
