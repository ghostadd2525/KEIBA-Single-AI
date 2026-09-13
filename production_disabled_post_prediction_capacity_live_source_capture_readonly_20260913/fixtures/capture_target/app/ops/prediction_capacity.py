"""CAPTURE_TOOL_FIXTURE — not Production bytes.

Used only to unit-test the read-only capture/extract tools.
Do not overlay this file onto origin/main.
Do not treat this SHA as a live SHA.
LIVE_BYTES=NO
STUB_OR_MOCK_SUCCESS=NO
"""

def get_with_meta(race_id):  # pragma: no cover
    raise RuntimeError("capture_tool_fixture_is_not_live_bytes")
