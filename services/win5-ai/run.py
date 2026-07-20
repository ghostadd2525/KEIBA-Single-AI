"""Entry point from repo root: python services/win5-ai/run.py"""
import runpy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# Single AI / AI Core: parent of KEIBA-Single-AI (or AI_PLATFORM_ROOT)
_platform = Path(__import__("os").environ.get("AI_PLATFORM_ROOT") or "")
if not _platform.is_dir():
    # services/win5-ai → … → platform root containing ai_platform/
    for candidate in (ROOT.parents[2], ROOT.parents[1], ROOT.parent):
        if (candidate / "ai_platform").is_dir():
            _platform = candidate
            break
if _platform.is_dir() and str(_platform) not in sys.path:
    sys.path.insert(0, str(_platform))
runpy.run_module("app.main", run_name="__main__")
