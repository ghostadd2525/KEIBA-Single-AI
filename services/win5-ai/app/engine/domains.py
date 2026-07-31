"""PredictionBundle contract + projections for sibling services."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

BUNDLE_SCHEMA = "single-prediction-bundle/2.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def score_percent(ai_confidence: dict[str, Any] | None) -> int | None:
    c = ai_confidence or {}
    if isinstance(c.get("score_percent"), (int, float)):
        return int(round(c["score_percent"]))
    score = c.get("score")
    if isinstance(score, (int, float)):
        return int(round(score * 100)) if score <= 1 else int(round(score))
    return None


def normalize_prediction_bundle(raw: dict[str, Any], race_id: str | None = None) -> dict[str, Any]:
    rid = race_id or raw.get("race_id") or (raw.get("race_info") or {}).get("race_id")
    info = dict(raw.get("race_info") or {})
    if rid:
        info["race_id"] = rid
    return {
        **raw,
        "schema_version": BUNDLE_SCHEMA,
        "race_id": rid,
        "race_info": info,
        "status": raw.get("status") or "ok",
        "warnings": raw.get("warnings") if isinstance(raw.get("warnings"), list) else [],
        "evaluation": raw.get("evaluation") or {"status": "unknown", "runners": []},
        "ai_confidence": raw.get("ai_confidence")
        or {
            "schema_version": "single-ai-confidence/1.0",
            "status": "unknown",
            "score": None,
            "band": "unknown",
        },
        "explain": raw.get("explain") or {"narrative": "", "reasons": [], "meta": {}},
        "betting_recommendations": raw.get("betting_recommendations")
        or {
            "schema_version": "single-betting-recommendations/1.0",
            "race_id": rid,
            "status": "unknown",
            "items": [],
        },
    }


def catalog_to_prediction_bundle(race: dict[str, Any], base: dict[str, Any] | None = None) -> dict[str, Any]:
    race_id = str(race.get("race_id") or race.get("public_race_id") or "").strip()
    if not race_id:
        raise KeyError("race_id")
    hint = race.get("ai_confidence")
    base_n = normalize_prediction_bundle(base, race_id) if base else None
    band = "unknown"
    if isinstance(hint, (int, float)):
        band = "high" if hint >= 85 else "medium" if hint >= 70 else "low"
    date = str(race.get("date") or "")
    venue = str(race.get("venue") or "")
    bundle = {
        "schema_version": BUNDLE_SCHEMA,
        "race_id": race_id,
        "generated_at": (base_n or {}).get("generated_at") or _now(),
        "model_version": (base_n or {}).get("model_version") or "list-projection",
        "core_version": (base_n or {}).get("core_version") or "list-projection",
        "product_version": (base_n or {}).get("product_version") or "expect-ui-0.1.0",
        "status": "ok",
        "warnings": [],
        "race_info": {
            "race_id": race_id,
            "date": race.get("date"),
            "venue": race.get("venue"),
            "meeting_id": f"{date.replace('-', '')}_{venue.lower()}",
            "race_no": race.get("race_no"),
            "post_time": race.get("post_time"),
            "distance": race.get("distance"),
            "surface": race.get("surface"),
            "course": ((base_n or {}).get("race_info") or {}).get("course"),
            "class_label": race.get("class_label"),
            "grade": race.get("badge"),
            "field_size": race.get("field_size"),
            "race_status": race.get("status") or "scheduled",
            "date_label": race.get("date_label"),
            "date_full": race.get("date_full"),
            "bg": race.get("bg"),
        },
        "evaluation": (base_n or {}).get("evaluation")
        or {"status": "list", "world": None, "sub_world": None, "runners": []},
        "ai_confidence": {
            "schema_version": "single-ai-confidence/1.0",
            "status": "ok",
            "score": (float(hint) / 100.0) if isinstance(hint, (int, float)) else None,
            "score_unit": "normalized",
            "band": band,
            "factors": [],
            "component_scores": {},
            "notes": "list projection",
            "computed_at": _now(),
        },
        "explain": (base_n or {}).get("explain") or {"meta": {}, "reasons": [], "narrative": ""},
        "betting_recommendations": (base_n or {}).get("betting_recommendations")
        or {
            "schema_version": "single-betting-recommendations/1.0",
            "race_id": race_id,
            "status": "list",
            "items": [],
            "by_bet_type": {},
        },
    }
    return normalize_prediction_bundle(bundle, race_id)


def project_confidence(bundle: dict[str, Any]) -> dict[str, Any]:
    b = normalize_prediction_bundle(bundle)
    c = b.get("ai_confidence") or {}
    return {
        "schema_version": "expect-confidence/1.0",
        "race_id": b.get("race_id"),
        "status": c.get("status") or "ok",
        "score": c.get("score"),
        "score_percent": score_percent(c),
        "score_unit": c.get("score_unit") or "normalized",
        "band": c.get("band") or "unknown",
        "factors": c.get("factors") or [],
        "component_scores": c.get("component_scores") or {},
        "notes": c.get("notes") or "",
        "computed_at": c.get("computed_at"),
    }


def project_tickets(bundle: dict[str, Any]) -> dict[str, Any]:
    b = normalize_prediction_bundle(bundle)
    br = b.get("betting_recommendations") or {}
    return {
        "schema_version": "expect-tickets/1.0",
        "race_id": b.get("race_id"),
        "status": br.get("status") or "ok",
        "strategy_id": br.get("strategy_id"),
        "generated_at": br.get("generated_at"),
        "items": br.get("items") or [],
        "by_bet_type": br.get("by_bet_type") or {},
    }


def to_analysis(row: dict[str, Any], race_id: str) -> dict[str, Any]:
    return {
        "schema_version": "expect-analysis/1.0",
        "race_id": race_id or row.get("race_id"),
        "charts": row.get("charts") or [],
        "overall": row.get("overall"),
        "narrative": row.get("narrative") or "",
    }


def kaoba_reply(body: dict[str, Any]) -> dict[str, Any]:
    """
    Kaoba rule fallback（Explain UX）。
    回答は必ず 結論 → 理由 → 補足。
    Bundle に馬名があるときは必ず明示。「この馬」「このレース」は最終フォールバックのみ。
    「本命馬」「Prediction」「対象馬」は使わない。
    Prediction/印/順位/スコアは変更しない。
    """
    message = str(body.get("message") or "")
    race_id = str(body.get("race_id") or "")
    ctx = body.get("context") or {}
    mode = str(ctx.get("mode") or body.get("mode") or "").lower()
    ctx_type = str(ctx.get("type") or "")
    has_strategy = ctx.get("ui") == "strategy" or ctx_type in (
        "strategy_review",
        "consult",
    )
    is_explain = mode in ("explain", "explain_pick") or ctx_type in (
        "honmei_reason",
        "explain_pick",
    )

    HELP = (
        "ごめんね、ちょっと質問の内容が分からなかったよ😅\n"
        "レースについてなら何でも聞いてね。"
    )
    CASUAL_GUIDE = "雑談したいときは通常のKAOBAチャットでも話せるよ😊"
    SUGGEST = ["なぜ本命？", "2番との差は？", "不安材料は？", "穴馬は？"]

    bundle = body.get("_bundle") if isinstance(body.get("_bundle"), dict) else None
    info = (bundle or {}).get("race_info") if isinstance((bundle or {}).get("race_info"), dict) else {}
    runners: list[dict[str, Any]] = []
    if bundle and isinstance(bundle.get("evaluation"), dict):
        runners = [r for r in (bundle["evaluation"].get("runners") or []) if isinstance(r, dict)]
    runners_sorted = sorted(runners, key=lambda r: int(r.get("model_rank") or 999))

    def _hl(r: dict[str, Any] | None) -> str:
        """実馬名優先。名前無しは空文字（呼び出し側で「この馬」最終 FB）。"""
        if not r:
            return ""
        num = r.get("horse_number")
        name = str(r.get("horse_name") or "").strip()
        if name:
            if num is not None and num != "":
                return f"{num}番{name}".strip()
            return name
        if num is not None and num != "":
            return f"{num}番"
        return ""

    honmei = next((r for r in runners_sorted if r.get("mark") == "honmei"), None)
    if not honmei and runners_sorted:
        honmei = runners_sorted[0]
    rival = next((r for r in runners_sorted if r is not honmei), None)
    ana_list = [r for r in runners_sorted if r.get("mark") in ("ana", "upset")]
    if not ana_list:
        ana_list = runners_sorted[2:4]
    ana_list = ana_list[:2]
    ana = ana_list[0] if ana_list else None

    h_name = _hl(honmei) or "この馬"
    h_bare = str((honmei or {}).get("horse_name") or "").strip() or h_name
    r_name = _hl(rival) or "2番手"
    a_names = [_hl(x) for x in ana_list if _hl(x)]
    a_name = a_names[0] if a_names else ""
    venue = str(info.get("venue") or "")
    race_no = info.get("race_no") if info.get("race_no") is not None else info.get("race_number")
    if venue and race_no is not None:
        place = f"{venue}{race_no}R"
    elif venue:
        place = venue
    elif race_id:
        place = race_id
    else:
        place = "このレース"
    distance = info.get("distance")
    field = info.get("field_size")
    surface = info.get("surface")

    ability = (honmei or {}).get("ability_scores") if isinstance((honmei or {}).get("ability_scores"), dict) else {}
    meta = {}
    if bundle and isinstance(bundle.get("explain"), dict):
        meta = bundle["explain"].get("meta") if isinstance(bundle["explain"].get("meta"), dict) else {}
    gap12 = meta.get("gap12")
    entropy = meta.get("entropy")
    try:
        gap12_f = float(gap12) if gap12 is not None else None
    except (TypeError, ValueError):
        gap12_f = None
    try:
        entropy_f = float(entropy) if entropy is not None else None
    except (TypeError, ValueError):
        entropy_f = None

    def _pct(v: Any) -> float | None:
        try:
            n = float(v)
        except (TypeError, ValueError):
            return None
        if n <= 1:
            return n * 100
        return n

    front = _pct(ability.get("front_rate"))
    dist_fit = _pct(ability.get("distance_score"))
    history = _pct(ability.get("history_score"))
    style_fit = _pct(ability.get("style_distance_fit_weight"))
    if style_fit is None:
        style_fit = _pct(ability.get("style_confidence"))
    pace_risk = ability.get("pace_collapse_risk_v2")
    try:
        pace_risk_f = (
            float(pace_risk) * (100 if float(pace_risk) <= 1 else 1)
            if pace_risk is not None
            else None
        )
    except (TypeError, ValueError):
        pace_risk_f = None
    pace_resilience = (100.0 - pace_risk_f) if pace_risk_f is not None else None

    try:
        dist_n = float(distance) if distance is not None else None
    except (TypeError, ValueError):
        dist_n = None
    try:
        field_n = int(field) if field is not None else None
    except (TypeError, ValueError):
        field_n = None

    def _dist_label() -> str | None:
        if dist_n is None:
            return None
        return str(int(dist_n) if dist_n == int(dist_n) else distance)

    def _hash_seed(s: str) -> int:
        h = 2166136261
        for ch in s:
            h ^= ord(ch)
            h = (h * 16777619) & 0xFFFFFFFF
        return h

    def merge_reason(lines: list[str], fallback: str) -> str:
        xs = [str(x).strip() for x in (lines or []) if str(x).strip()]
        if not xs:
            return fallback
        if len(xs) == 1:
            return xs[0]
        return f"{_strip_yo(xs[0])}し、{xs[1]}"

    def _strip_yo(s: str) -> str:
        t = str(s or "").strip().rstrip("。．")
        if t.endswith("だよ"):
            return t[:-2]
        if t.endswith("よ"):
            return t[:-1]
        return t

    def compose_explain(conclusion: str, reason: str, supplement: str) -> str:
        return "\n".join([p for p in (conclusion, reason, supplement) if p])

    def collect_evidence() -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        dlab = _dist_label()

        if venue or surface:
            course = f"{venue}の{surface}" if venue and surface else (venue or str(surface))
            items.append(
                {
                    "kind": "course",
                    "strength": 55,
                    "why": f"{course}らしい流れになりやすく、そこで運べる馬が残るイメージだよ",
                    "gap": f"{course}では、どの位置から直線に入れるかの差が出やすいよ",
                    "risk": f"{course}で想定と違う流れになると、直線まで脚が持たなくなりやすいよ",
                }
            )
            if venue:
                items.append(
                    {
                        "kind": "course_flow",
                        "strength": 52,
                        "why": f"{venue}では序盤の位置取りが、その後の流れを決めやすいよ",
                        "gap": f"{venue}では、取りたい位置を取れたかどうかで差が開きやすいよ",
                        "risk": f"{venue}で想定外の先行争いになると、後半に息が上がりやすいよ",
                    }
                )

        if dist_n is not None and dlab is not None:
            if dist_n <= 1400:
                dist_why = "短い距離なので、出して好位に付けた馬が最後まで残りやすいよ"
                dist_risk = "出遅れると、追い上げる間もなく終わってしまいやすいよ"
                dist_gap = "短い距離では、序盤に前へ行けた側が残りやすいよ"
            elif dist_n <= 1800:
                dist_why = "道中の運びと、最後の直線での伸びの両方が効きやすい距離だよ"
                dist_risk = "ペースを誤ると、最後の直線で勢いが落ちやすいよ"
                dist_gap = f"{int(dist_n)}mでは、直線でどれだけ脚を使えるかの差が出やすいよ"
            else:
                dist_why = "長い距離なので、後半まで脚を使える馬が残りやすいよ"
                dist_risk = "後半につかれてしまうと、直線で差されやすくなるよ"
                dist_gap = "長い距離では、後半に脚が残るかどうかで差が出やすいよ"
            items.append(
                {
                    "kind": "distance",
                    "strength": 60,
                    "why": dist_why,
                    "gap": dist_gap,
                    "risk": dist_risk,
                }
            )

        if dist_fit is not None:
            if dist_fit >= 70:
                items.append(
                    {
                        "kind": "distance_fit",
                        "strength": 85,
                        "why": (
                            f"今回の{dlab}mでも、最後まで脚が残りやすいタイプだよ"
                            if dlab
                            else "今回の距離でも、最後まで脚が残りやすいタイプだよ"
                        ),
                        "gap": f"距離の向きでは、{h_name} の方が直線まで楽に運べそうだよ",
                        "risk": None,
                    }
                )
            elif dist_fit < 45:
                items.append(
                    {
                        "kind": "distance_fit",
                        "strength": 30,
                        "why": None,
                        "gap": "距離の向きでは、どちらも決め手になりにくいよ",
                        "risk": (
                            f"今回の{dlab}mは得意と言えず、後半につかれると崩れやすいよ"
                            if dlab
                            else "今回の距離は得意と言えず、後半につかれると崩れやすいよ"
                        ),
                    }
                )

        if front is not None:
            if front >= 70:
                items.append(
                    {
                        "kind": "style",
                        "strength": 80,
                        "why": f"{h_name} は前めの位置から押していける形が合いやすいよ",
                        "gap": f"前で運べるかどうかで、{h_name} の方が楽に見えるよ",
                        "risk": f"{h_name} は前に行けないと、得意な形を作れず苦しくなりやすいよ",
                    }
                )
            elif front >= 40:
                items.append(
                    {
                        "kind": "style",
                        "strength": 65,
                        "why": "中団あたりで様子を見ながら運べるタイプだよ",
                        "gap": "中団の取り合いになると、位置取りの差が出やすいよ",
                        "risk": "中団が詰まると、進路を失って直線で伸びきれないよ",
                    }
                )
            else:
                items.append(
                    {
                        "kind": "style",
                        "strength": 50,
                        "why": f"{h_name} は後ろから差してくる形が合いやすいよ",
                        "gap": f"差せる展開かどうかで、{h_name} と対抗の見え方が変わるよ",
                        "risk": f"{h_name} は前が止まらない展開だと、差せないまま終わりやすいよ",
                    }
                )

        if pace_risk_f is not None:
            if pace_risk_f >= 40:
                items.append(
                    {
                        "kind": "pace",
                        "strength": 45,
                        "why": None,
                        "gap": "前半が速くなりやすく、粘れる馬と苦しくなる馬で差が出やすいよ",
                        "risk": "前半の流れが速くなると、直線で息が上がって差されやすいよ",
                    }
                )
            elif pace_risk_f < 20:
                items.append(
                    {
                        "kind": "pace",
                        "strength": 75,
                        "why": "落ち着いた流れになりやすく、前で運んだ馬が粘りやすいよ",
                        "gap": "落ち着いた流れなら、前で運べる側が差を広げやすいよ",
                        "risk": "想定より速い流れになると、粘れず崩れやすいよ",
                    }
                )
            else:
                items.append(
                    {
                        "kind": "pace",
                        "strength": 55,
                        "why": "極端な流れにはなりにくく、標準的な運びになりやすいよ",
                        "gap": "標準的な流れでは、細かい位置取りの差が残りやすいよ",
                        "risk": "ペース配分を誤ると、直線で勢いが落ちやすいよ",
                    }
                )

        if history is not None:
            if history >= 70:
                items.append(
                    {
                        "kind": "ability",
                        "strength": 82,
                        "why": f"{h_name} は近走もしっかり走れていて、今回も同じ水準を出せそうだよ",
                        "gap": f"近走の内容では、{h_name} の方が安定して見えやすいよ",
                        "risk": None,
                    }
                )
            elif history < 45:
                items.append(
                    {
                        "kind": "ability",
                        "strength": 35,
                        "why": None,
                        "gap": "近走だけだと、差がはっきりしないよ",
                        "risk": "近走が波打っているので、同じ走りが出ないと崩れやすいよ",
                    }
                )
            else:
                items.append(
                    {
                        "kind": "ability",
                        "strength": 58,
                        "why": "近走はまずまずで、大きなマイナスは目立たないよ",
                        "gap": "近走だけでは、差が小さいよ",
                        "risk": None,
                    }
                )

        if pace_resilience is not None:
            if pace_resilience >= 70:
                items.append(
                    {
                        "kind": "stability",
                        "strength": 78,
                        "why": f"{h_name} は流れが多少乱れても、最後まで形を崩しにくいよ",
                        "gap": f"流れが少し荒れても、{h_name} の方が粘りやすいよ",
                        "risk": None,
                    }
                )
            elif pace_resilience < 45:
                items.append(
                    {
                        "kind": "stability",
                        "strength": 32,
                        "why": None,
                        "gap": "流れが乱れたときの粘りでは、差が開きにくいよ",
                        "risk": "流れが乱れると、最後の直線で勢いが落ちやすいよ",
                    }
                )

        if style_fit is not None:
            if style_fit >= 70:
                items.append(
                    {
                        "kind": "style_fit",
                        "strength": 76,
                        "why": f"{h_name} は想定している流れとの相性が良いよ",
                        "gap": f"流れとの相性では、{h_name} の方が有利に見えやすいよ",
                        "risk": None,
                    }
                )
            elif style_fit < 45:
                items.append(
                    {
                        "kind": "style_fit",
                        "strength": 34,
                        "why": None,
                        "gap": None,
                        "risk": "想定と違う流れになると、一気に苦しくなりやすいよ",
                    }
                )

        if field_n is not None:
            if field_n >= 15:
                items.append(
                    {
                        "kind": "field",
                        "strength": 50,
                        "why": None,
                        "gap": f"出走{field_n}頭と多く、馬群の中で差が埋もれやすいよ",
                        "risk": f"出走{field_n}頭だと馬群に包まれ、進路が取れないと崩れやすいよ",
                    }
                )
            elif field_n <= 10:
                items.append(
                    {
                        "kind": "field",
                        "strength": 62,
                        "why": f"出走{field_n}頭と少なめで、実力差が出やすい並びだよ",
                        "gap": "少頭数なので、2頭の差が着順に出やすいよ",
                        "risk": None,
                    }
                )
        return items

    def pick_evidence(items: list[dict[str, Any]], mode: str, n: int) -> list[str]:
        scored: list[tuple[float, str, str]] = []
        for it in items:
            text = it.get(mode)
            if not text:
                continue
            strength = float(it.get("strength") or 50)
            if mode == "risk":
                score = 100.0 - strength
            elif mode == "gap":
                score = abs(strength - 50) + strength * 0.3
            else:
                score = strength
            scored.append((score, str(it.get("kind") or ""), str(text)))
        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[str] = []
        kinds: set[str] = set()
        for _score, kind, text in scored:
            if kind in kinds:
                continue
            kinds.add(kind)
            out.append(text)
            if len(out) >= n:
                break
        return out

    def _sub(msg: str) -> str:
        m = (msg or "").strip()
        if not m:
            return "unknown"
        casual_keys = (
            "こんにちは",
            "こんばんは",
            "おはよう",
            "やあ",
            "はじめまして",
            "hello",
            "疲れた",
            "つかれた",
            "お疲れ",
            "おつかれ",
            "眠い",
            "ねむい",
            "元気",
            "調子",
            "気分",
            "暑い",
            "寒い",
            "天気",
            "雨",
            "ありがとう",
            "サンキュ",
            "雑談",
            "おしゃべり",
            "暇",
        )
        if any(k in m for k in ("雨なら", "雨だと", "重馬場", "不良馬場", "天候")):
            return "weather"
        if "オッズ" in m:
            return "odds"
        if any(k in m for k in ("少額", "予算")):
            return "budget"
        if any(k in m for k in ("見送", "パスする", "買わない", "休むべき")):
            return "skip"
        if any(k in m for k in ("初心者", "初めて", "入門", "わかりやすく")):
            return "beginner"
        if any(k in m for k in ("この買い", "買い方どう", "戦略どう", "どう思う")):
            return "bet"
        if is_explain and any(
            k.lower() in m.lower() if k.isascii() else k in m for k in casual_keys
        ):
            # 裸の「雨」は雑談になり得るが、相談文脈の雨ならは上で処理済み
            return "casual"
        if any(k in m for k in ("差", "対抗", "2番", "二番", "比較", "違い")):
            return "gap"
        if any(k in m for k in ("不安", "リスク", "危険", "弱点", "心配")):
            return "risk"
        if any(k in m for k in ("買い方", "買い目", "どう買う", "点数", "流し")):
            return "bet"
        if any(k in m for k in ("穴馬", "穴", "大穴", "波乱", "一発")):
            return "upset"
        if any(k in m for k in ("理由", "なぜ", "根拠", "どうして", "本命", "◎")):
            return "why"
        if is_explain:
            return "unknown"
        return "other"

    sub = _sub(message)
    evidence = collect_evidence()
    reply = None
    emotion = "fun"
    suggestions = SUGGEST

    CONSULT_CHIPS = ["この買い方どう？", "見送るべき？", "初心者なら？"]
    EXPLAIN_REDIRECT = (
        "その内容は「予想の説明」で確認できるよ。\n"
        "馬の理由や差・不安・穴の話はそちらが向いているよ。\n"
        "ここでは買い方や立ち回りの相談を続けよう。"
    )
    ROOM_REDIRECT = (
        "その話ならルームチャットで話そう😊\n"
        "ここではレースや買い方の相談を中心に案内しているよ。"
    )

    # 相談AIモード: Greeting → Explain → Strategy / 雑談
    if has_strategy and not is_explain:
        if re.search(
            r"こんにちは|こんばんは|おはよう|やあ|はじめまして|hello|hi\b|ハロー|お疲れ|おつかれ|ありがとう|どうも|サンキュ",
            message,
            re.I,
        ) and not re.search(
            r"買い|資金|少額|予算|見送|雨|馬場|オッズ|初心|戦略|◎|本命|穴馬|不安",
            message,
        ):
            if re.search(r"ありがとう|どうも|サンキュ", message):
                soft = "どういたしまして😊"
            elif re.search(r"お疲れ|おつかれ", message):
                soft = "お疲れさま😊"
            elif "おはよう" in message:
                soft = "おはよう😊"
            elif "こんばんは" in message:
                soft = "こんばんは😊"
            else:
                soft = "こんにちは😊"
            reply = (
                soft
                + "\nレースや買い方について気になることがあれば、一緒に考えるよ。"
            )
            emotion = "fun"
            suggestions = CONSULT_CHIPS
        elif sub == "casual":
            reply = ROOM_REDIRECT
            emotion = "fun"
            suggestions = CONSULT_CHIPS
        elif sub in ("why", "gap", "upset") or any(
            k in message for k in ("なぜ", "◎", "2番との差", "不安材料", "穴馬", "穴候補")
        ):
            reply = EXPLAIN_REDIRECT
            emotion = "fun"
            suggestions = CONSULT_CHIPS

    if reply:
        pass
    elif sub == "unknown":
        if has_strategy and not is_explain:
            reply = ROOM_REDIRECT
            suggestions = CONSULT_CHIPS
        else:
            reply = HELP
            suggestions = SUGGEST
        emotion = "fun"
    elif sub == "casual":
        soft = "うん、聞いてるよ。"
        if "おはよう" in message:
            soft = "おはよう！"
        elif "こんばんは" in message:
            soft = "こんばんは！"
        elif any(k in message for k in ("こんにちは", "はじめまして", "やあ")) or "hello" in message.lower():
            soft = "こんにちは！"
        elif any(k in message for k in ("疲れた", "つかれた", "お疲れ", "おつかれ", "眠い", "ねむい")):
            soft = "お疲れさま。少し休んでね。"
        elif "暑い" in message:
            soft = "だよね、暑いね。"
        elif "寒い" in message:
            soft = "だよね、寒いね。"
        elif any(k in message for k in ("ありがとう", "サンキュ", "どうも")):
            soft = "どういたしまして。"
        reply = f"{soft}\n{CASUAL_GUIDE}\nレースについてはここで案内できるよ。"
        emotion = "fun"
        suggestions = SUGGEST
    elif sub == "why":
        reasons = pick_evidence(evidence, "why", 2)
        reason = (
            f"近走内容・距離・展開の相性をまとめて見ると、{h_bare}が一番安定して走れそうだったよ。"
            if reasons
            else "近走内容・距離・展開の相性をまとめて見ると、一番安定して走れそうだったよ。"
        )
        reply = compose_explain(
            f"{h_name}を◎にした一番の理由は、今回の条件なら一番力を発揮しやすいと判断したからだよ。",
            reason,
            f"だから今回は{h_bare}を中心に考えているよ。",
        )
        emotion = "joy"
        suggestions = ["2番との差は？", "不安材料は？", "穴馬は？"]
    elif sub == "gap":
        dims = pick_evidence(evidence, "gap", 2) or [
            "位置取りと、直線での伸び方の差が出やすいよ"
        ]
        top = dims[0]
        reason = merge_reason(dims[:2], top)
        if gap12_f is not None and gap12_f >= 0.04:
            conclusion = f"{h_name}と{r_name}を比べると、{top}"
            wrap = f"だから今回は{h_bare}を一歩前に見ているよ。"
        elif gap12_f is not None and gap12_f < 0.02:
            conclusion = f"{r_name}も強いけど、{h_name}との差は小さいよ。"
            wrap = "入れ替わる余地は残るので、差は薄いと見ていいよ。"
        else:
            conclusion = f"2番の{r_name}も強いけど、今回は{h_name}側の位置取りを評価したよ。"
            wrap = f"差はあるけど詰められる範囲で、中心は{h_bare}だよ。"
        reply = compose_explain(conclusion, reason, wrap)
        emotion = "joy"
        suggestions = ["なぜ本命？", "不安材料は？", "穴馬は？"]
    elif sub == "risk":
        risks = pick_evidence(evidence, "risk", 2) or [
            "想定と違うペースになると、位置を取れず苦しくなりやすいよ",
            "前が止まらない展開だと、狙った形を作れないよ",
        ]
        top = risks[0]
        reason = merge_reason(
            risks[:2],
            "想定と違う流れになると、力を出しにくくなりやすいよ。",
        )
        reply = compose_explain(
            f"{h_name}で一番心配なのは、{_strip_yo(top)}ことだよ。",
            reason,
            f"もしその流れになると、{h_bare}も力を出しにくくなるよ。",
        )
        emotion = "fun"
        suggestions = ["なぜ本命？", "2番との差は？", "穴馬は？"]
    elif sub == "bet" or sub == "betting":
        reply = (
            f"この買い方なら、{h_name}を中心に進めて大丈夫だと思うよ。\n"
            "大きく崩すより、点数と総額を守るほうが安心。\n"
            "少額・見送り・雨・オッズの話も、気になるところから聞いてね。"
        )
        emotion = "fun"
        suggestions = CONSULT_CHIPS
    elif sub == "skip" or any(k in message for k in ("見送", "パスする", "買わない")):
        reply = compose_explain(
            "迷うなら、無理に大きく買わず見送り寄りでいいよ。",
            "自信が薄いときは総額を抑えるか、主軸だけ少額にするのが無難。",
            "今日の調子に合わせて、無理しない立ち回りを優先しよう。",
        )
        emotion = "fun"
        suggestions = CONSULT_CHIPS
    elif sub == "beginner" or any(k in message for k in ("初心者", "初めて", "入門")):
        reply = compose_explain(
            "初心者なら、主軸（馬連・ワイド）を少点数で買うのがおすすめだよ。",
            "保険や一発は後回しにして、総額も普段どおりに抑えよう。",
            f"軸の {h_name} を中心に、相手は広げすぎないのが安心。",
        )
        emotion = "fun"
        suggestions = CONSULT_CHIPS
    elif sub in ("weather",) or any(k in message for k in ("雨なら", "雨だと", "重馬場", "不良")):
        reply = compose_explain(
            "雨なら、前が残るか崩れやすいかが変わりやすいよ。",
            "軸は変えず、相手を1頭増減して様子を見るのが無難。",
            "馬場発表を見てから最終判断しよう。",
        )
        emotion = "fun"
        suggestions = CONSULT_CHIPS
    elif sub == "odds" or "オッズ" in message:
        reply = compose_explain(
            "オッズが動いても、軸をすぐ変えないのがおすすめだよ。",
            "人気が急に集まった相手は点数を少し抑えめに。",
            "総額の上限は守ったまま調整しよう。",
        )
        emotion = "fun"
        suggestions = CONSULT_CHIPS
    elif sub == "budget" or "少額" in message or "予算" in message:
        reply = compose_explain(
            "少額なら、主軸（馬連・ワイド）に寄せるのがおすすめだよ。",
            "保険や一発は後回しにして、総額を普段どおりに抑えよう。",
            f"軸の {h_name} 中心はそのままで大丈夫。",
        )
        emotion = "fun"
        suggestions = CONSULT_CHIPS
    elif has_strategy and sub in ("unknown", "general", "", "other"):
        reply = ROOM_REDIRECT
        emotion = "joy"
        suggestions = CONSULT_CHIPS
    elif sub == "upset":
        if len(a_names) >= 2:
            conclusion = f"穴候補として見たいのは{a_names[0]}と{a_names[1]}だよ。"
        elif a_names:
            conclusion = f"穴候補として見たいのは{a_names[0]}だよ。"
        else:
            conclusion = "穴を探すなら、上位以外で今回の距離・流れが合う馬だよ。"
        upset_bits: list[str] = []
        if entropy_f is not None and entropy_f >= 2.2:
            upset_bits.append("上位が接戦なので、人気薄が一気に上がりやすい並びだよ")
        if pace_risk_f is not None and pace_risk_f >= 40:
            upset_bits.append("前半が速くなると、前の人気馬より後ろからの馬が残りやすいよ")
        if field_n is not None and field_n >= 15:
            upset_bits.append(f"出走{field_n}頭と多く、伏兵が紛れやすいよ")
        if dist_n is not None:
            if dist_n <= 1400:
                upset_bits.append("短い距離では、序盤の位置取り次第で人気薄が残ることがあるよ")
            else:
                upset_bits.append(f"{int(dist_n)}mが合う人気薄は、直線で伸びてくることがあるよ")
        if not upset_bits:
            upset_bits.extend(pick_evidence(evidence, "gap", 2))
        reason = merge_reason(upset_bits[:2], "今回の流れに合いそうな人気薄を拾ったよ。")
        a_bare = str((ana_list[0] or {}).get("horse_name") or "").strip() if ana_list else ""
        tip_name = a_bare or (a_names[0] if a_names else "")
        wrap = (
            f"だから{tip_name}は相手の端に残しておきたいよ。"
            if tip_name
            else f"{place}では、条件が合う人気薄を端に置いておく感じだよ。"
        )
        reply = compose_explain(conclusion, reason, wrap)
        emotion = "fun"
        suggestions = ["なぜ本命？", "不安材料は？", "2番との差は？"]
    elif any(k in message for k in ("展開", "ペース")):
        pace_bits = pick_evidence(evidence, "why", 1) or pick_evidence(evidence, "risk", 1)
        reply = (
            pace_bits[0]
            if pace_bits
            else "展開はペース想定が外れると位置取りが変わりやすいよ。レース画面のAI解説もあわせて見てね。"
        )
        emotion = "fun"
        suggestions = SUGGEST
    elif "血統" in message:
        reply = "血統面ではコース適性が高い産駒が目立ってるよ。"
        emotion = "fun"
        suggestions = SUGGEST
    else:
        reply = HELP if is_explain else compose_explain(
            f"{place}では◎の{h_name}を中心に見ているよ。",
            f"{h_bare}の走り方と、今回の距離・展開の相性が良さそうに見えるよ。",
            "知りたい内容に合わせて、「なぜ本命？」「2番との差は？」「不安材料は？」「穴馬は？」のどれかで聞いてね。",
        )
        emotion = "fun" if is_explain else "joy"
        suggestions = SUGGEST

    return {
        "schema_version": "expect-kaoba/1.0",
        "reply": reply,
        "emotion": emotion,
        "suggestions": suggestions,
        "referenced_race_id": race_id or None,
        "provider": "rule",
        "intent": sub if sub != "other" else "general",
        "live2d": {
            "emotion": emotion,
            "motion": "talk_happy" if emotion == "joy" else "talk_idle",
            "expression": "smile" if emotion == "joy" else "neutral",
        },
    }



# backward-compatible aliases used by older imports
def to_prediction(bundle: dict[str, Any], race_id: str) -> dict[str, Any]:
    return normalize_prediction_bundle(bundle, race_id)


def to_confidence(bundle: dict[str, Any], race_id: str) -> dict[str, Any]:
    return project_confidence(normalize_prediction_bundle(bundle, race_id))


def to_tickets(bundle: dict[str, Any], race_id: str) -> dict[str, Any]:
    return project_tickets(normalize_prediction_bundle(bundle, race_id))


def to_prediction_summary(race: dict[str, Any]) -> dict[str, Any]:
    b = catalog_to_prediction_bundle(race)
    return {"race_id": b["race_id"], "confidence_hint": score_percent(b.get("ai_confidence"))}
