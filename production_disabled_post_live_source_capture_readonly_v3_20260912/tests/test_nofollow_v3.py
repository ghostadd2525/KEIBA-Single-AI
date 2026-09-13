#!/usr/bin/env python3
from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import live_source_capture as cap
from test_live_source_capture import V6_DIR, copy_tree, run_capture, systemd_fixture


def no_payload(stdout: str) -> None:
    if "=== TAR_BASE64_BEGIN ===" in stdout:
        raise AssertionError("payload leaked\n%s" % stdout)
    if "TAR_PAYLOAD=OMITTED_INCOMPLETE" not in stdout:
        raise AssertionError("expected omitted payload\n%s" % stdout)


class SymlinkAndContainmentTests(unittest.TestCase):
    def test_symlink_main_py_is_stop_and_omits_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outside = Path(td) / "outside.py"
            outside.write_text("SECRET_OUTSIDE\n", encoding="utf-8")
            win5 = Path(td) / "services" / "win5-ai"
            copy_tree(V6_DIR, win5)
            target = win5 / "app" / "main.py"
            target.unlink()
            target.symlink_to(outside)
            self.assertTrue(target.is_file())
            self.assertTrue(stat.S_ISLNK(os.lstat(target).st_mode))
            rc, stdout = run_capture(win5, prepare=None)
            self.assertNotEqual(rc, 0)
            self.assertIn("CAPTURE_RESULT=STOP", stdout)
            self.assertIn("STOP_REASON=capture_symlink:app/main.py", stdout)
            self.assertNotIn("SECRET_OUTSIDE", stdout)
            no_payload(stdout)

    def test_one_of_three_symlink_omits_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outside = Path(td) / "outside.py"
            outside.write_text("SECRET_OUTSIDE\n", encoding="utf-8")
            win5 = Path(td) / "services" / "win5-ai"
            copy_tree(V6_DIR, win5)
            link = win5 / "app" / "core" / "feature_loader_bridge.py"
            link.unlink()
            link.symlink_to(outside)
            rc, stdout = run_capture(win5, prepare=None)
            self.assertNotEqual(rc, 0)
            self.assertIn("STOP_REASON=capture_symlink:app/core/feature_loader_bridge.py", stdout)
            no_payload(stdout)

    def test_intermediate_dir_symlink_outside_is_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outside_root = Path(td) / "outside_app"
            outside_root.mkdir()
            (outside_root / "main.py").write_text("SECRET_VIA_DIR_LINK\n", encoding="utf-8")
            win5 = Path(td) / "services" / "win5-ai"
            copy_tree(V6_DIR, win5)
            app = win5 / "app"
            # Keep other capture files; only replace the app directory with a symlink
            # after moving repository/core aside? Simpler: replace app/main.py's
            # parent by linking app -> outside that contains only main.py and
            # the other required children as regular copies.
            real_repo = (win5 / "app" / "data" / "repository" / "__init__.py").read_bytes()
            real_bridge = (win5 / "app" / "core" / "feature_loader_bridge.py").read_bytes()
            (outside_root / "data" / "repository").mkdir(parents=True)
            (outside_root / "core").mkdir(parents=True)
            (outside_root / "data" / "repository" / "__init__.py").write_bytes(real_repo)
            (outside_root / "core" / "feature_loader_bridge.py").write_bytes(real_bridge)
            # swap app dir for symlink
            tmp_app = win5 / "app.real"
            app.rename(tmp_app)
            app.symlink_to(outside_root)
            rc, stdout = run_capture(win5, prepare=None)
            self.assertNotEqual(rc, 0)
            self.assertIn("CAPTURE_RESULT=STOP", stdout)
            self.assertTrue(
                "capture_outside_win5:" in stdout or "capture_symlink:" in stdout,
                msg=stdout,
            )
            self.assertNotIn("SECRET_VIA_DIR_LINK", stdout)
            no_payload(stdout)

    def test_non_regular_fifo_is_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            copy_tree(V6_DIR, win5)
            # Keep app/main.py as a regular file so win5 discovery still
            # succeeds; the non-regular target is one of the other two.
            target = win5 / "app" / "core" / "feature_loader_bridge.py"
            target.unlink()
            os.mkfifo(target)
            rc, stdout = run_capture(win5, prepare=None)
            self.assertNotEqual(rc, 0)
            self.assertIn(
                "STOP_REASON=capture_not_regular:app/core/feature_loader_bridge.py",
                stdout,
            )
            no_payload(stdout)

    def test_symlink_to_file_inside_win5_is_still_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            copy_tree(V6_DIR, win5)
            target = win5 / "app" / "main.py"
            inside = win5 / "app" / "core" / "feature_loader_bridge.py"
            target.unlink()
            target.symlink_to(inside)
            rc, stdout = run_capture(win5, prepare=None)
            self.assertNotEqual(rc, 0)
            self.assertIn("STOP_REASON=capture_symlink:app/main.py", stdout)
            no_payload(stdout)

    def test_read_readonly_rejects_symlink_without_following(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            outside = root / "outside.py"
            outside.write_bytes(b"SECRET_DIRECT")
            rel = "app/main.py"
            path = root / rel
            path.parent.mkdir(parents=True)
            path.symlink_to(outside)
            with self.assertRaises(cap.CaptureOpenError) as ctx:
                cap.read_readonly(path, win5_real=root.resolve(), rel=rel)
            self.assertTrue(str(ctx.exception).startswith("capture_symlink:"))

    def test_open_fd_outside_win5_is_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outside = Path(td) / "outside.py"
            outside.write_text("SECRET_FD_OUTSIDE\n", encoding="utf-8")
            win5 = Path(td) / "services" / "win5-ai"
            copy_tree(V6_DIR, win5)
            target = win5 / "app" / "main.py"
            real_open = os.open

            def open_outside(name, flags, *args, **kwargs):
                if os.fspath(name) == os.fspath(target):
                    return real_open(os.fspath(outside), flags, *args, **kwargs)
                return real_open(name, flags, *args, **kwargs)

            fixture = systemd_fixture(win5)
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with patch.object(cap, "systemd_show", return_value=fixture):
                with patch.object(os, "open", side_effect=open_outside):
                    with redirect_stdout(buf):
                        rc = cap.main()
            stdout = buf.getvalue()
            self.assertNotEqual(rc, 0)
            self.assertIn("CAPTURE_RESULT=STOP", stdout)
            self.assertIn("STOP_REASON=capture_outside_win5:app/main.py", stdout)
            self.assertNotIn("SECRET_FD_OUTSIDE", stdout)
            no_payload(stdout)

    def test_after_open_swap_to_symlink_is_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outside = Path(td) / "outside.py"
            outside.write_text("SECRET_AFTER_OPEN\n", encoding="utf-8")
            win5 = Path(td) / "services" / "win5-ai"
            copy_tree(V6_DIR, win5)
            target = win5 / "app" / "main.py"
            real_open = os.open

            def open_then_swap(name, flags, *args, **kwargs):
                fd = real_open(name, flags, *args, **kwargs)
                if os.fspath(name) == os.fspath(target):
                    os.unlink(name)
                    os.symlink(outside, name)
                return fd

            fixture = systemd_fixture(win5)
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with patch.object(cap, "systemd_show", return_value=fixture):
                with patch.object(os, "open", side_effect=open_then_swap):
                    with redirect_stdout(buf):
                        rc = cap.main()
            stdout = buf.getvalue()
            self.assertNotEqual(rc, 0)
            self.assertIn("CAPTURE_RESULT=STOP", stdout)
            self.assertTrue(
                any(
                    key in stdout
                    for key in (
                        "capture_unlinked:app/main.py",
                        "capture_symlink:app/main.py",
                        "capture_path_changed:app/main.py",
                    )
                ),
                msg=stdout,
            )
            self.assertNotIn("SECRET_AFTER_OPEN", stdout)
            no_payload(stdout)

    def test_open_swap_to_symlink_is_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outside = Path(td) / "outside.py"
            outside.write_text("SECRET_SWAP\n", encoding="utf-8")
            win5 = Path(td) / "services" / "win5-ai"
            copy_tree(V6_DIR, win5)
            target = win5 / "app" / "main.py"
            real_open = os.open

            def swap_then_open(name, flags, *args, **kwargs):
                if os.path.samefile(name, target) or os.fspath(name) == os.fspath(target):
                    os.unlink(name)
                    os.symlink(outside, name)
                return real_open(name, flags, *args, **kwargs)

            fixture = systemd_fixture(win5)
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with patch.object(cap, "systemd_show", return_value=fixture):
                with patch.object(os, "open", side_effect=swap_then_open):
                    with redirect_stdout(buf):
                        rc = cap.main()
            stdout = buf.getvalue()
            self.assertNotEqual(rc, 0)
            self.assertIn("CAPTURE_RESULT=STOP", stdout)
            self.assertIn("STOP_REASON=capture_symlink:app/main.py", stdout)
            self.assertNotIn("SECRET_SWAP", stdout)
            no_payload(stdout)


if __name__ == "__main__":
    unittest.main()
