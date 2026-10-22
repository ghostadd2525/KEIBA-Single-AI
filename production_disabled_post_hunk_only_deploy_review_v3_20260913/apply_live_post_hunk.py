#!/usr/bin/env python3
"""Apply review-v6 POST route insertions to live Production main.py bytes.

Does not talk to Production. Does not replace main.py wholesale.
Applies exactly two insertions at unique live markers.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent
LIVE_MAIN = PACK / "live_canon" / "app" / "main.py"
DEFAULT_OUT = PACK / "candidates" / "services" / "win5-ai" / "app" / "main.py"

EXPECTED_LIVE_SHA256 = (
    "7486a9ad7578e9ccdf883eaaac85f0b0de7ba329e286302b8d2f57db81d79235"
)
EXPECTED_HUNKED_SHA256 = (
    "a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c"
)
EXPECTED_HUNKED_SIZE = 48345

DO_OPTIONS_MARK = "    def do_OPTIONS(self) -> None:  # noqa: N802\n"
DO_POST_BLOCK = (
    "    def do_POST(self) -> None:  # noqa: N802\n"
    "        parsed = urlparse(self.path)\n"
    "        path = parsed.path\n"
    "        self._begin_request(path)\n"
    "\n"
    "        bad = self._check_key()\n"
)

INSERTION_1 = """    def _handle_prediction_runs_post(self) -> None:
        # Disabled check must run before importing the POST implementation
        # module (app.predictions.runs). If that import later raises,
        # disabled mode still returns 503 PREDICTION_RUNS_DISABLED.
        raw = (os.environ.get("PREDICTION_RUNS_ENABLED") or "0").strip().lower()
        if raw not in {"1", "true", "yes"}:
            self._send(*err("PREDICTION_RUNS_DISABLED", "PREDICTION_RUNS_ENABLED is not 1", 503))
            return
        from .predictions.guards import (
            ERROR_AUTH_REQUIRED,
            ERROR_BODY_TOO_LARGE,
            ERROR_RATE_LIMITED,
            check_prediction_run_rate_limit,
            parse_prediction_run_content_length,
            prediction_run_body_limit_bytes,
            verify_prediction_run_auth,
        )
        from .predictions.runs import handle_post_prediction_run

        length = parse_prediction_run_content_length(self.headers.get("Content-Length"))
        limit = prediction_run_body_limit_bytes()
        if length is None or length > limit:
            self._send(*err(ERROR_BODY_TOO_LARGE, "request body exceeds limit", 413))
            return
        try:
            verify_prediction_run_auth(self.headers)
            ident = (
                self.headers.get("X-Prediction-Run-Key")
                or self.headers.get("X-AI-Key")
                or self.client_address[0]
            )
            check_prediction_run_rate_limit(str(ident))
        except Exception as exc:
            code = getattr(exc, "code", None)
            if code == ERROR_AUTH_REQUIRED:
                self._send(*err(ERROR_AUTH_REQUIRED, str(exc), 401))
                return
            if code == ERROR_RATE_LIMITED:
                self._send(*err(ERROR_RATE_LIMITED, str(exc), 429))
                return
            raise
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(*err("BAD_REQUEST", "JSON body required", 400))
            return
        status, payload = handle_post_prediction_run(body if isinstance(body, dict) else {})
        self._send(status, payload)

"""

INSERTION_2 = (
    "        if path == \"/v1/prediction-runs\":\n"
    "            self._handle_prediction_runs_post()\n"
    "            return\n"
    "\n"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply_hunks(src: str) -> str:
    if src.count(DO_OPTIONS_MARK) != 1:
        raise RuntimeError("do_OPTIONS_marker_not_unique:%s" % src.count(DO_OPTIONS_MARK))
    if "_handle_prediction_runs_post" in src:
        raise RuntimeError("already_contains_prediction_runs_handler")
    if src.count(DO_POST_BLOCK) != 1:
        raise RuntimeError("do_POST_block_not_unique:%s" % src.count(DO_POST_BLOCK))
    if src.count("    def do_PATCH(self) -> None:  # noqa: N802\n") != 1:
        raise RuntimeError("do_PATCH_missing_or_not_unique")
    out = src.replace(DO_OPTIONS_MARK, INSERTION_1 + DO_OPTIONS_MARK, 1)
    post_with_branch = DO_POST_BLOCK.replace(
        "        bad = self._check_key()\n",
        INSERTION_2 + "        bad = self._check_key()\n",
        1,
    )
    out = out.replace(DO_POST_BLOCK, post_with_branch, 1)
    if out.count("_handle_prediction_runs_post") != 2:
        raise RuntimeError("handler_ref_count:%s" % out.count("_handle_prediction_runs_post"))
    patch_idx = out.find("    def do_PATCH(self) -> None:  # noqa: N802\n")
    post_idx = out.find("    def do_POST(self) -> None:  # noqa: N802\n")
    if "if path == \"/v1/prediction-runs\":" not in out[post_idx:patch_idx if patch_idx > post_idx else None]:
        raise RuntimeError("do_POST_missing_prediction_runs_branch")
    if "if path == \"/v1/prediction-runs\":" in out[patch_idx:]:
        raise RuntimeError("do_PATCH_must_not_gain_prediction_runs_branch")
    return out


def apply_path(src_path: Path, dest_path: Path | None = None) -> bytes:
    raw = src_path.read_bytes()
    text = raw.decode("utf-8")
    out = apply_hunks(text).encode("utf-8")
    if dest_path is not None:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(out)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=LIVE_MAIN)
    parser.add_argument("--dest", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--expect-live-sha256", default=EXPECTED_LIVE_SHA256)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    raw = args.src.read_bytes()
    live_sha = sha256_bytes(raw)
    if live_sha != args.expect_live_sha256:
        print("LIVE_SHA_MISMATCH", live_sha, file=sys.stderr)
        return 2
    dest = args.dest if args.write else None
    out = apply_path(args.src, dest)
    print("LIVE_SHA256=%s" % live_sha)
    print("HUNKED_SIZE=%s" % len(out))
    print("HUNKED_SHA256=%s" % sha256_bytes(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
