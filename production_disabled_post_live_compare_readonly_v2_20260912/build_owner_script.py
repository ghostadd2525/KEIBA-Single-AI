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
# Read-only Production live compare v2. Paste on the Production SSH host.
# Do not copy files onto Production. Do not redirect this script to a file
# on the Production host. Stdout only.
# Forbids: write, restart, env change, migrate, POST, deploy, APPLY.
# Canonical file: OWNER_LIVE_COMPARE.sh
# Presented file: OWNER_PASTE_COMMAND_BLOCK.sh
# These two files are generated as byte-identical copies.
set -u
export LC_ALL=C

echo "===== BEGIN OWNER_READ_ONLY_LIVE_COMPARE_V2 ====="
echo "PACK=production_disabled_post_live_compare_readonly_v2_20260912"
echo "V4_REVIEW_BUNDLE=PASS"
echo "V4_ZIP_SHA256=77ecd36924719fbcfd3cdb0a58e19fc8160013e6267201be48e1199634676f74"
echo "V1_LIVE_COMPARE_PACK_NOT_OVERWRITTEN=YES"
echo "PRODUCTION_CODE_DEPLOY_ALLOWED=NO"
echo "OWNER_DEPLOY_APPROVED=NO"
echo "POST_CODE_PRODUCTION_DEPLOYED=NO"
echo "CURSOR_PRODUCTION_SSH=NO"
echo "THIS_SCRIPT_WRITES=NO"
echo "HOST=$(hostname 2>/dev/null || echo UNKNOWN)"
echo "WHEN_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo UNKNOWN)"

python3 - <<'PY'
"""

FOOTER = """
PY

rc=$?
echo "===== END OWNER_READ_ONLY_LIVE_COMPARE_V2 ====="
exit "$rc"
"""


def main() -> int:
    body = SRC.read_text(encoding="utf-8")
    if "PY\n" in body or body.endswith("PY"):
        # The marker must remain unique in the wrapper.
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
