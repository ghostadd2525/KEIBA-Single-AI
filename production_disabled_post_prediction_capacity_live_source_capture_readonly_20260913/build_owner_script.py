#!/usr/bin/env python3
"""Build Owner paste scripts from live_source_capture.py. Both outputs are byte-identical."""
from __future__ import annotations

import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent
SRC = PACK / "live_source_capture.py"
CANON = PACK / "OWNER_LIVE_SOURCE_CAPTURE.sh"
PRESENTED = PACK / "OWNER_PASTE_COMMAND_BLOCK.sh"

HEADER = """#!/usr/bin/env bash
# Read-only Production live-source capture. Paste on the Production SSH host.
# Do not copy files onto Production. Do not redirect this script to a file
# on the Production host. Stdout only. Windows saves the transcript.
# Forbids: write, restart, env change, migrate, POST, deploy, APPLY, SCP.
# Canonical file: OWNER_LIVE_SOURCE_CAPTURE.sh
# Presented file: OWNER_PASTE_COMMAND_BLOCK.sh
# These two files are generated as byte-identical copies.
set -u
export LC_ALL=C

echo "===== BEGIN OWNER_READ_ONLY_PREDICTION_CAPACITY_CAPTURE ====="
echo "PACK=production_disabled_post_prediction_capacity_live_source_capture_readonly_20260913"
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
"""

FOOTER = """
PY

rc=$?
echo "===== END OWNER_READ_ONLY_PREDICTION_CAPACITY_CAPTURE ====="
exit "$rc"
"""


def main() -> int:
    body = SRC.read_text(encoding="utf-8")
    if "\nPY\n" in body:
        raise SystemExit("live_source_capture.py contains a lone PY line; wrapper would break")
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
