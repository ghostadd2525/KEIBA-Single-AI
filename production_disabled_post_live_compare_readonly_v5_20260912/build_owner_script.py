#!/usr/bin/env python3
"""Build Owner paste scripts from live_compare.py. Both outputs are byte-identical."""
from __future__ import annotations

import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent
SRC = PACK / "live_compare.py"
CANON = PACK / "OWNER_LIVE_COMPARE.sh"
PRESENTED = PACK / "OWNER_PASTE_COMMAND_BLOCK.sh"

HEADER = """#!/usr/bin/env bash
# Read-only Production live compare v5. Paste on the Production SSH host.
# Do not copy files onto Production. Do not redirect this script to a file
# on the Production host. Stdout only.
# Forbids: write, restart, env change, migrate, POST, deploy, APPLY.
# Canonical file: OWNER_LIVE_COMPARE.sh
# Presented file: OWNER_PASTE_COMMAND_BLOCK.sh
# These two files are generated as byte-identical copies.
# Canon hashes: code-deploy review v6. Do not run live-compare v4.
set -u
export LC_ALL=C

echo "===== BEGIN OWNER_READ_ONLY_LIVE_COMPARE_V5 ====="
echo "PACK=production_disabled_post_live_compare_readonly_v5_20260912"
echo "V6_REVIEW_BUNDLE=PASS"
echo "V6_ZIP_SHA256=548b274facc2b4f8ffba8b854a6e009d8b7455fb816dcde9550eb9b364329373"
echo "LIVE_COMPARE_V4_DO_NOT_RUN=YES"
echo "V1_LIVE_COMPARE_PACK_NOT_OVERWRITTEN=YES"
echo "V2_LIVE_COMPARE_PACK_NOT_OVERWRITTEN=YES"
echo "V3_LIVE_COMPARE_PACK_NOT_OVERWRITTEN=YES"
echo "V4_LIVE_COMPARE_PACK_NOT_OVERWRITTEN=YES"
echo "PRODUCTION_CODE_DEPLOY_ALLOWED=NO"
echo "OWNER_DEPLOY_APPROVED=NO"
echo "POST_CODE_PRODUCTION_DEPLOYED=NO"
echo "OWNER_EXECUTE_NOW=NO"
echo "CURSOR_PRODUCTION_SSH=NO"
echo "THIS_SCRIPT_WRITES=NO"
echo "HOST=$(hostname 2>/dev/null || echo UNKNOWN)"
echo "WHEN_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo UNKNOWN)"

python3 - <<'PY'
"""

FOOTER = """
PY

rc=$?
echo "===== END OWNER_READ_ONLY_LIVE_COMPARE_V5 ====="
exit "$rc"
"""


def main() -> int:
    body = SRC.read_text(encoding="utf-8")
    if "\nPY\n" in body:
        raise SystemExit("live_compare.py contains a lone PY line; wrapper would break")
    text = HEADER + body
    if not text.endswith("\n"):
        text += "\n"
    text += FOOTER
    if not text.endswith("\n"):
        text += "\n"
    CANON.write_text(text, encoding="utf-8")
    PRESENTED.write_text(text, encoding="utf-8")
    CANON.chmod(0o755)
    PRESENTED.chmod(0o755)
    if CANON.read_bytes() != PRESENTED.read_bytes():
        raise SystemExit("canonical and presented scripts are not identical")
    print("WROTE %s" % CANON.name)
    print("WROTE %s identical=%s" % (PRESENTED.name, "YES"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
