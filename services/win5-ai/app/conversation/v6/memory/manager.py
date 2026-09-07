# -*- coding: utf-8 -*-
"""
Memory Manager — Candidate → Consent → Store の正規フロー。

自動保存禁止: consent なし / Policy 拒否は Store に書かない。
"""
from __future__ import annotations

import threading
from typing import Any

from .consent import ConsentManager
from .models import MemoryCandidate, MemoryRecord
from .policy import MemoryPolicy
from .retriever import MemoryRetriever
from .store import MemoryStore, get_memory_store


class MemoryManager:
    """Memory Platform の中核オーケストレーション（V4 Orchestrator とは別）。"""

    version = "v6-phase2"

    def __init__(
        self,
        *,
        store: MemoryStore | None = None,
        policy: MemoryPolicy | None = None,
        consent: ConsentManager | None = None,
        retriever: MemoryRetriever | None = None,
    ) -> None:
        self.store = store or get_memory_store()
        self.policy = policy or MemoryPolicy()
        self.consent = consent or ConsentManager()
        self.retriever = retriever or MemoryRetriever(store=self.store)

    def build_candidate(self, user_id: str, message: str) -> MemoryCandidate:
        consent_ok = self.consent.has_explicit_remember_consent(message)
        return self.policy.extract_candidate(
            user_id=user_id,
            message=message,
            consent_detected=consent_ok,
        )

    def remember(self, user_id: str, message: str) -> dict[str, Any]:
        """
        Conversation → Memory Candidate → User Consent → Memory Store
        """
        candidate = self.build_candidate(user_id, message)

        if not candidate.consent_detected:
            return {
                "ok": False,
                "action": "remember",
                "saved": False,
                "reason": "consent_required",
                "message": "保存には「覚えて」など明示的な許可が必要です。自動では記憶しません。",
                "candidate": candidate.to_dict(),
            }

        if candidate.rejected_reason:
            return {
                "ok": False,
                "action": "remember",
                "saved": False,
                "reason": candidate.rejected_reason,
                "message": "その内容は Memory の保存対象外です。",
                "candidate": candidate.to_dict(),
            }

        record = MemoryRecord.create(
            user_id=user_id,
            category=candidate.category,
            key=candidate.key,
            value=candidate.value,
            source_text=candidate.source_text,
            consent=True,
            meta={"flow": "consent_only", "auto_save": False},
        )
        saved = self.store.upsert(record)
        return {
            "ok": True,
            "action": "remember",
            "saved": True,
            "message": f"覚えました：({saved.category}) {saved.value}",
            "record": saved.to_dict(),
            "candidate": candidate.to_dict(),
        }

    def forget(self, user_id: str, message: str) -> dict[str, Any]:
        # 「〜を忘れて」から対象語を粗く抽出
        q = message
        for token in ("を忘れて", "忘れて", "忘れろ", "を削除して", "削除して"):
            if token in q:
                q = q.split(token, 1)[0]
                break
        q = q.strip(" 　「」『』")
        removed = self.store.delete_matching(user_id, q) if q else []
        if not removed and q:
            # クエリが弱い場合は value 部分一致を再試行せず空結果
            pass
        return {
            "ok": True,
            "action": "forget_one",
            "removed_count": len(removed),
            "removed": [r.to_dict() for r in removed],
            "message": (
                f"{len(removed)}件忘れました。"
                if removed
                else "該当する記憶が見つかりませんでした。"
            ),
        }

    def forget_all(self, user_id: str) -> dict[str, Any]:
        n = self.store.clear(user_id)
        return {
            "ok": True,
            "action": "forget_all",
            "removed_count": n,
            "message": "あなたの長期 Memory をすべて削除しました。" if n else "記憶はありませんでした。",
        }

    def list_memories(self, user_id: str) -> dict[str, Any]:
        data = self.retriever.as_dict(user_id)
        records = data.get("memories") or []
        if not records:
            msg = "いま覚えている長期 Memory はありません。"
        else:
            lines = ["あなたについて覚えていること:"]
            for r in records:
                lines.append(f"・[{r.get('category')}] {r.get('value')}")
            msg = "\n".join(lines)
        return {
            **data,
            "action": "list",
            "message": msg,
        }

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": self.version,
            "auto_save": False,
            "consent_required": True,
            "store": self.store.meta(),
            "policy": self.policy.meta(),
            "consent": self.consent.meta(),
            "separated_from": [
                "conversation_history",
                "knowledge",
                "prediction",
                "security",
            ],
        }


_MANAGER: MemoryManager | None = None
_MANAGER_LOCK = threading.Lock()


def get_memory_manager() -> MemoryManager:
    global _MANAGER
    with _MANAGER_LOCK:
        if _MANAGER is None:
            _MANAGER = MemoryManager()
        return _MANAGER


def reset_memory_manager_for_tests(store: MemoryStore | None = None) -> MemoryManager:
    global _MANAGER
    with _MANAGER_LOCK:
        _MANAGER = MemoryManager(store=store) if store is not None else MemoryManager()
        return _MANAGER
