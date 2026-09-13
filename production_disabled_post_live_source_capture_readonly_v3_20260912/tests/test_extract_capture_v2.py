#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import io
import re
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import extract_capture as ex
import live_source_capture as cap
from test_live_source_capture import V6_DIR, run_capture

BEGIN = "=== TAR_BASE64_BEGIN ==="
END = "=== TAR_BASE64_END ==="


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def good_transcript() -> str:
    with tempfile.TemporaryDirectory() as td:
        win5 = Path(td) / "services" / "win5-ai"
        rc, stdout = run_capture(win5)
        if rc != 0:
            raise AssertionError("fixture capture failed\n%s" % stdout)
        return stdout


def split_payload(text: str) -> tuple[str, str, str]:
    start = text.find(BEGIN)
    end = text.find(END)
    return text[:start], text[start + len(BEGIN) : end], text[end + len(END) :]


def rebuild_with_blob(text: str, blob: bytes) -> str:
    prefix, _old, suffix = split_payload(text)
    b64 = base64.b64encode(blob).decode("ascii")
    wrapped = "\n".join(b64[i : i + 76] for i in range(0, len(b64), 76))
    prefix = re.sub(r"(?m)^TAR_GZ_BYTES=\d+$", "TAR_GZ_BYTES=%s" % len(blob), prefix)
    prefix = re.sub(r"(?m)^TAR_GZ_SHA256=[0-9a-f]{64}$", "TAR_GZ_SHA256=%s" % sha256_bytes(blob), prefix)
    prefix = re.sub(r"(?m)^TAR_B64_CHARS=\d+$", "TAR_B64_CHARS=%s" % len(b64), prefix)
    prefix = re.sub(
        r"(?m)^TAR_B64_SHA256=[0-9a-f]{64}$",
        "TAR_B64_SHA256=%s" % sha256_bytes(b64.encode("ascii")),
        prefix,
    )
    return prefix + BEGIN + "\n" + wrapped + "\n" + END + suffix


def tar_from_pairs(pairs: list[tuple[str, bytes]], *, kinds: list[str] | None = None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.USTAR_FORMAT) as tar:
        for i, (name, data) in enumerate(pairs):
            info = tarfile.TarInfo(name=name)
            kind = (kinds[i] if kinds else "reg")
            if kind == "reg":
                info.type = tarfile.REGTYPE
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = "somewhere"
                info.size = 0
                tar.addfile(info)
            elif kind == "hardlink":
                info.type = tarfile.LNKTYPE
                info.linkname = pairs[0][0]
                info.size = 0
                tar.addfile(info)
            else:
                raise AssertionError(kind)
    return buf.getvalue()


def extract_stop(text: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        tr = Path(td) / "transcript.txt"
        dest = Path(td) / "extracted"
        tr.write_text(text, encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = ex.main([str(tr), "--out", str(dest)])
        stdout = buf.getvalue()
        if rc == 0 or "EXTRACT_RESULT=STOP" not in stdout:
            raise AssertionError("expected STOP\n%s" % stdout)
        if dest.exists():
            leftover = [p.as_posix() for p in dest.rglob("*") if p.is_file()]
            raise AssertionError("partial files written: %s\n%s" % (leftover, stdout))
        if "EXTRACTED_FILE_COUNT=0" not in stdout:
            raise AssertionError("expected EXTRACTED_FILE_COUNT=0\n%s" % stdout)
        return stdout


class ExtractHappyPathTests(unittest.TestCase):
    def test_valid_transcript_writes_three_files(self) -> None:
        text = good_transcript()
        with tempfile.TemporaryDirectory() as td:
            tr = Path(td) / "transcript.txt"
            dest = Path(td) / "extracted"
            tr.write_text(text, encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = ex.main([str(tr), "--out", str(dest)])
            self.assertEqual(rc, 0, msg=buf.getvalue())
            self.assertIn("EXTRACT_RESULT=GO", buf.getvalue())
            for rel in cap.CAPTURE_RELS:
                self.assertTrue((dest / rel).is_file())
                self.assertEqual((dest / rel).read_bytes(), (V6_DIR / rel).read_bytes())


class ExtractRequiredCounterexampleTests(unittest.TestCase):
    def test_zero_records(self) -> None:
        text = good_transcript()
        text = re.sub(r"(?m)^CAPTURE_REL=.*\n", "", text)
        text = re.sub(r"(?m)^CAPTURE_PATH=.*\n", "", text)
        text = re.sub(r"(?m)^CAPTURE_SIZE=.*\n", "", text)
        text = re.sub(r"(?m)^CAPTURE_SHA256=.*\n", "", text)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=capture_rel_count=0", out)

    def test_one_record(self) -> None:
        text = good_transcript()
        rels = re.findall(r"(?m)^CAPTURE_REL=.*$", text)
        self.assertEqual(len(rels), 3)
        text = text.replace(rels[1] + "\n", "").replace(rels[2] + "\n", "")
        out = extract_stop(text)
        self.assertIn("STOP_REASON=capture_rel_count=", out)

    def test_two_records(self) -> None:
        text = good_transcript()
        rels = re.findall(r"(?m)^CAPTURE_REL=.*$", text)
        text = text.replace(rels[2] + "\n", "")
        out = extract_stop(text)
        self.assertIn("STOP_REASON=capture_rel_count=", out)

    def test_duplicate_record(self) -> None:
        text = good_transcript()
        first = re.search(r"(?m)^CAPTURE_REL=.*$", text).group(0)
        text = text.replace(first, first + "\n" + first, 1)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=capture_rel_", out)

    def test_duplicate_begin_marker(self) -> None:
        text = good_transcript()
        text = text.replace(BEGIN, BEGIN + "\n" + BEGIN, 1)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=marker_count_begin=2", out)

    def test_duplicate_end_marker(self) -> None:
        text = good_transcript()
        text = text.replace(END, END + "\n" + END, 1)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=marker_count_begin=1_end=2", out)

    def test_stop_and_go_mixed(self) -> None:
        text = good_transcript()
        text = text.replace("CAPTURE_RESULT=GO", "CAPTURE_RESULT=STOP\nCAPTURE_RESULT=GO", 1)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=capture_result_mixed", out)

    def test_sha_missing(self) -> None:
        text = good_transcript()
        text = re.sub(r"(?m)^CAPTURE_SHA256=[0-9a-f]{64}$", "CAPTURE_SHA256=ABSENT", text, count=1)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=capture_sha_missing:", out)

    def test_size_missing(self) -> None:
        text = good_transcript()
        text = re.sub(r"(?m)^CAPTURE_SIZE=\d+$", "CAPTURE_SIZE=ABSENT", text, count=1)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=capture_size_missing:", out)

    def test_sha_mismatch(self) -> None:
        text = good_transcript()
        bad = "0" * 64
        text = re.sub(r"(?m)^CAPTURE_SHA256=[0-9a-f]{64}$", "CAPTURE_SHA256=%s" % bad, text, count=1)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=sha_mismatch:", out)

    def test_size_mismatch(self) -> None:
        text = good_transcript()
        text = re.sub(r"(?m)^CAPTURE_SIZE=\d+$", "CAPTURE_SIZE=1", text, count=1)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=size_mismatch:", out)

    def test_b64_chars_mismatch(self) -> None:
        text = good_transcript()
        text = re.sub(r"(?m)^TAR_B64_CHARS=\d+$", "TAR_B64_CHARS=1", text)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=tar_b64_chars_mismatch", out)

    def test_b64_hash_mismatch(self) -> None:
        text = good_transcript()
        text = re.sub(r"(?m)^TAR_B64_SHA256=[0-9a-f]{64}$", "TAR_B64_SHA256=%s" % ("ab" * 32), text)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=tar_b64_sha256_mismatch", out)

    def test_tar_gz_bytes_mismatch(self) -> None:
        text = good_transcript()
        text = re.sub(r"(?m)^TAR_GZ_BYTES=\d+$", "TAR_GZ_BYTES=1", text)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=tar_gz_bytes_mismatch", out)

    def test_tar_gz_hash_mismatch(self) -> None:
        text = good_transcript()
        text = re.sub(r"(?m)^TAR_GZ_SHA256=[0-9a-f]{64}$", "TAR_GZ_SHA256=%s" % ("cd" * 32), text)
        out = extract_stop(text)
        self.assertIn("STOP_REASON=tar_gz_sha256_mismatch", out)

    def _pairs(self) -> list[tuple[str, bytes]]:
        return [(rel, (V6_DIR / rel).read_bytes()) for rel in cap.CAPTURE_RELS]

    def test_extra_member(self) -> None:
        text = good_transcript()
        pairs = self._pairs() + [("app/extra.py", b"extra")]
        out = extract_stop(rebuild_with_blob(text, tar_from_pairs(pairs)))
        self.assertIn("STOP_REASON=tar_member_", out)

    def test_duplicate_member(self) -> None:
        text = good_transcript()
        pairs = [self._pairs()[0], self._pairs()[0], self._pairs()[1]]
        out = extract_stop(rebuild_with_blob(text, tar_from_pairs(pairs)))
        self.assertTrue(
            "STOP_REASON=tar_member_duplicate" in out or "STOP_REASON=tar_member_" in out,
            msg=out,
        )

    def test_symlink_member(self) -> None:
        text = good_transcript()
        pairs = self._pairs()
        kinds = ["symlink", "reg", "reg"]
        out = extract_stop(rebuild_with_blob(text, tar_from_pairs(pairs, kinds=kinds)))
        self.assertIn("STOP_REASON=symlink_member", out)

    def test_hardlink_member(self) -> None:
        text = good_transcript()
        pairs = self._pairs()
        kinds = ["reg", "hardlink", "reg"]
        out = extract_stop(rebuild_with_blob(text, tar_from_pairs(pairs, kinds=kinds)))
        self.assertIn("STOP_REASON=hardlink_member", out)

    def test_absolute_member(self) -> None:
        text = good_transcript()
        pairs = [("/tmp/evil.py", b"x"), self._pairs()[1], self._pairs()[2]]
        out = extract_stop(rebuild_with_blob(text, tar_from_pairs(pairs)))
        self.assertTrue(
            "absolute_member" in out or "tar_member_" in out,
            msg=out,
        )

    def test_dotdot_member(self) -> None:
        text = good_transcript()
        pairs = [("../evil.py", b"x"), self._pairs()[1], self._pairs()[2]]
        out = extract_stop(rebuild_with_blob(text, tar_from_pairs(pairs)))
        self.assertTrue(
            "dotdot_member" in out or "tar_member_" in out,
            msg=out,
        )


if __name__ == "__main__":
    unittest.main()
