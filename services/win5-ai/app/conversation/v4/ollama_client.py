# -*- coding: utf-8 -*-
"""Optional Ollama client — Casual Agent の言い換え用。Orchestrator 本体ではない。"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class OllamaResult:
    ok: bool
    reply: str = ""
    model: str | None = None
    error_reason: str | None = None


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_ms: int = 12000,
        chat_path: str = "/api/chat",
        tags_path: str = "/api/tags",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = max(timeout_ms, 1) / 1000.0
        self.chat_path = chat_path
        self.tags_path = tags_path

    def health(self) -> dict[str, Any]:
        url = f"{self.base_url}{self.tags_path}"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw else {}
            models = [m.get("name") for m in (data.get("models") or []) if m.get("name")]
            return {"ok": True, "reachable": True, "models": models, "error_reason": None}
        except Exception as exc:
            return {
                "ok": False,
                "reachable": False,
                "models": [],
                "error_reason": type(exc).__name__,
            }

    def chat(self, *, model: str, message: str) -> OllamaResult:
        url = f"{self.base_url}{self.chat_path}"
        payload = {
            "model": model,
            "stream": False,
            "messages": [{"role": "user", "content": message}],
        }
        try:
            raw_req = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=raw_req,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
            msg = (body.get("message") or {}).get("content") or body.get("response") or ""
            if not str(msg).strip():
                return OllamaResult(ok=False, error_reason="empty_reply", model=model)
            return OllamaResult(ok=True, reply=str(msg).strip(), model=model)
        except urllib.error.HTTPError as exc:
            return OllamaResult(ok=False, error_reason=f"http_{exc.code}", model=model)
        except Exception as exc:
            return OllamaResult(ok=False, error_reason=type(exc).__name__, model=model)
