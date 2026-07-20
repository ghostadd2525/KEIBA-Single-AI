# -*- coding: utf-8 -*-
"""
Reason Builder — Prediction / Coverage / Diagnostics から会話用説明を組み立て。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_FALLBACK_HELP: dict[str, str] = {
    "race_not_found": "レース情報（races.csv / DB）に該当行がありません。",
    "feature_csv_missing": "特徴量 CSV ファイル自体が見つかりません。",
    "market_feature_missing": "特徴量 CSV に当該レースの出走馬行がありません。",
    "feature_missing": "推論に必要な特徴量列が不足しています。",
    "platform_missing": "AI プラットフォーム (ai_platform) が未配置です。",
    "model_not_loaded": "推論モデルがロードされていません。",
    "prediction_failed": "推論処理が失敗しました。",
    "timeout": "推論がタイムアウトしました。",
    "exception": "推論中に例外が発生しました。",
}


@dataclass
class ReasonPayload:
    summary: str
    bullets: list[str]
    top_runners: list[dict[str, Any]]
    ai_confidence: float | None
    citations: list[dict[str, Any]]
    narrative: str
    sections: list[dict[str, str]] = field(default_factory=list)


class ReasonBuilder:
    def build(
        self,
        intent: str,
        tool_data: dict[str, Any],
        *,
        race_id: str | None = None,
        prediction_meta: dict[str, Any] | None = None,
    ) -> ReasonPayload:
        handlers = {
            "coverage_inquiry": self._coverage,
            "diagnostics_inquiry": self._diagnostics,
            "list_races": self._list_races,
            "greeting": self._greeting,
        }
        if intent in handlers:
            return handlers[intent](tool_data)

        pred = (tool_data.get("prediction") or {})
        bundle = pred.get("bundle")
        meta = prediction_meta or pred.get("meta")
        if not bundle:
            return self._no_data(intent, race_id, meta)

        return self._from_prediction(intent, bundle, meta, race_id=race_id)

    def _from_prediction(
        self,
        intent: str,
        bundle: dict[str, Any],
        meta: dict[str, Any] | None,
        *,
        race_id: str | None,
    ) -> ReasonPayload:
        runners = ((bundle.get("evaluation") or {}).get("runners")) or []
        top = runners[:3]
        conf = (bundle.get("ai_confidence") or {}).get("score")
        narrative = ((bundle.get("explain") or {}).get("narrative")) or ""
        rid = race_id or bundle.get("race_id")
        info = bundle.get("race_info") or {}
        venue_label = f"{info.get('venue', '')}{info.get('race_no', '')}R".strip()

        sections: list[dict[str, str]] = []
        citations: list[dict[str, Any]] = [{"type": "prediction_bundle", "race_id": rid}]
        bullets: list[str] = []

        engine = (meta or {}).get("engine_source")
        fb_reason = (meta or {}).get("fallback_reason")

        if engine == "real_ai":
            sections.append({"title": "推論", "body": "AI 実推論 (real_ai) で評価しました。"})
        elif engine in ("mock_fallback", "mock"):
            sections.append({"title": "推論", "body": "現在は参考データ (mock) で応答しています。"})
            if fb_reason:
                hint = _FALLBACK_HELP.get(str(fb_reason), str(fb_reason))
                bullets.append(f"フォールバック理由: {fb_reason} — {hint}")
                citations.append({"type": "fallback_reason", "code": fb_reason})

        if intent == "explain_pick":
            reasons = (bundle.get("explain") or {}).get("reasons") or []
            for r in reasons[:3]:
                bullets.extend(r.get("bullets") or [])
            summary = f"{venue_label or rid} の選定理由です。"
            if not bullets:
                bullets = [narrative or "詳細理由は限定的です。"]
        elif intent == "find_upset":
            ana = next((r for r in runners if r.get("mark") == "ana"), None)
            if not ana and len(runners) >= 4:
                ana = runners[3]
            if ana:
                summary = (
                    f"穴候補: {ana.get('horse_number')}番 "
                    f"{ana.get('horse_name') or ''}"
                )
                bullets = ["モデル評価上位の下位人気候補を確認してください。"]
            else:
                summary = "穴印の馬は現データにありません。"
                bullets = ["人気薄で評価が相対的に高い馬を手動確認してください。"]
        elif intent == "buy_advice":
            honmei = next((r for r in runners if r.get("mark") == "honmei"), top[0] if top else None)
            if honmei:
                prob = honmei.get("win_prob")
                prob_txt = f"{float(prob):.1%}" if isinstance(prob, (int, float)) else "—"
                summary = (
                    f"本命候補 {honmei.get('horse_number')}番 "
                    f"{honmei.get('horse_name') or ''}（勝率目安 {prob_txt}）"
                )
                bullets = [
                    "軸は本命中心で点数を抑える",
                    "相手は対抗・穴から広げる",
                    "確信度が低い場合は見送りも選択肢",
                ]
            else:
                summary = "買い目の軸候補を特定できませんでした。"
        else:
            names = " / ".join(
                f"{r.get('horse_number')}番{r.get('horse_name') or ''}" for r in top
            )
            conf_txt = f"{float(conf):.1%}" if isinstance(conf, (int, float)) else "—"
            summary = f"{venue_label or rid} の AI 評価トップ: {names or '—'}（確信度 {conf_txt}）"
            if narrative:
                bullets.append(narrative)

        if top:
            sections.append(
                {
                    "title": "上位3頭",
                    "body": "、".join(
                        f"{r.get('horse_number')}番({r.get('win_prob', '—')})" for r in top
                    ),
                }
            )

        return ReasonPayload(
            summary=summary,
            bullets=bullets,
            top_runners=top,
            ai_confidence=conf if isinstance(conf, (int, float)) else None,
            citations=citations,
            narrative=narrative,
            sections=sections,
        )

    def _no_data(
        self,
        intent: str,
        race_id: str | None,
        meta: dict[str, Any] | None,
    ) -> ReasonPayload:
        bullets = ["レースを指定してください。例: 今日の福島11R / 20260719_fukushima_11"]
        if meta and meta.get("fallback_reason"):
            bullets.insert(0, f"理由: {meta['fallback_reason']}")
        return ReasonPayload(
            summary="対象レースの予想データが見つかりませんでした。",
            bullets=bullets,
            top_runners=[],
            ai_confidence=None,
            citations=[],
            narrative="",
        )

    def _coverage(self, tool_data: dict[str, Any]) -> ReasonPayload:
        cov = tool_data.get("coverage") or {}
        total = cov.get("race_total", 0)
        real = cov.get("real_ai", 0)
        mock = cov.get("mock", 0)
        pct = cov.get("coverage", 0)
        summary = (
            f"データカバレッジ: {pct}%（全{total}レース中 real_ai {real} / mock {mock}）"
        )
        bullets = [
            f"不足レース (race_not_found 系): {cov.get('missing_races', 0)}",
            f"不足特徴量: {cov.get('missing_features', 0)}",
        ]
        by_reason = cov.get("by_reason") or {}
        if by_reason:
            bullets.append(
                "内訳: " + ", ".join(f"{k}={v}" for k, v in list(by_reason.items())[:4])
            )
        return ReasonPayload(
            summary=summary,
            bullets=bullets,
            top_runners=[],
            ai_confidence=None,
            citations=[{"type": "coverage_api"}],
            narrative="",
            sections=[{"title": "Coverage", "body": summary}],
        )

    def _diagnostics(self, tool_data: dict[str, Any]) -> ReasonPayload:
        diag = tool_data.get("diagnostics") or {}
        summary_data = diag.get("summary") or {}
        fb = tool_data.get("fallback") or {}
        total_mock = fb.get("total_mock", summary_data.get("mock_fallback", 0))
        summary = f"診断: mock_fallback {total_mock} 件。データ追加で real_ai 化可能な項目を確認してください。"
        bullets: list[str] = []
        for row in (diag.get("how_to_reach_real_ai") or [])[:3]:
            reason = row.get("fallback_reason", "")
            count = row.get("count", 0)
            remediation = row.get("remediation", "")
            bullets.append(f"{reason} ({count}件): {remediation}")
        if not bullets:
            bullets = ["`/v1/diagnostics/missing` で詳細レポートを確認できます。"]
        return ReasonPayload(
            summary=summary,
            bullets=bullets,
            top_runners=[],
            ai_confidence=None,
            citations=[{"type": "diagnostics_api"}],
            narrative="",
            sections=[{"title": "Diagnostics", "body": summary}],
        )

    def _list_races(self, tool_data: dict[str, Any]) -> ReasonPayload:
        races = tool_data.get("races") or []
        if not races:
            return ReasonPayload(
                summary="本日のレース一覧は取得できませんでした。",
                bullets=["カタログが空の可能性があります。"],
                top_runners=[],
                ai_confidence=None,
                citations=[],
                narrative="",
            )
        lines = [
            f"{r.get('venue')}{r.get('race_no')}R ({r.get('race_id')})" for r in races[:8]
        ]
        summary = f"直近カタログ {len(races)} 件（先頭8件を表示）"
        return ReasonPayload(
            summary=summary,
            bullets=lines,
            top_runners=[],
            ai_confidence=None,
            citations=[{"type": "race_catalog"}],
            narrative="",
            sections=[{"title": "レース一覧", "body": "\n".join(lines)}],
        )

    def _greeting(self, tool_data: dict[str, Any]) -> ReasonPayload:
        caps = (tool_data.get("help") or {}).get("capabilities") or []
        summary = "Expect 競馬 AI アシスタントです。自然言語で予想・診断をお手伝いします。"
        return ReasonPayload(
            summary=summary,
            bullets=list(caps),
            top_runners=[],
            ai_confidence=None,
            citations=[{"type": "help"}],
            narrative="",
            sections=[{"title": "できること", "body": "\n".join(caps)}],
        )
