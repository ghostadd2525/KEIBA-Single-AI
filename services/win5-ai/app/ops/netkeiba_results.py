# -*- coding: utf-8 -*-
"""
Netkeiba official race result fetch + parse (Production Result Sync).

Does not touch Prediction Engine / Candidate Evaluation.
Uses race.netkeiba.com result HTML + PI catalog for Win5 race_id mapping.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Callable

RESULT_URL = "https://race.netkeiba.com/race/result.html?race_id={race_id}"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_YEN_RE = re.compile(r"([\d,]+)\s*円")
_HORSE_ROW_RE = re.compile(
    r'<tr[^>]*class="[^"]*HorseList[^"]*"[^>]*>(.*?)</tr>',
    re.I | re.S,
)
_PAYOUT_TABLE_RE = re.compile(
    r'<table[^>]*class="[^"]*Payout_Detail_Table[^"]*"[^>]*>(.*?)</table>',
    re.I | re.S,
)


class NetkeibaResultError(Exception):
    pass


def _strip_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", text).strip()


def _parse_yen_list(raw: str) -> list[int]:
    out: list[int] = []
    for m in _YEN_RE.finditer(raw or ""):
        try:
            out.append(int(m.group(1).replace(",", "")))
        except ValueError:
            continue
    return out


def _parse_int_tokens(raw: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", raw or "")]


def parse_finish_order(html: str) -> list[int]:
    """Return horse numbers in finish order (1st → last)."""
    pairs: list[tuple[int, int]] = []
    for row in _HORSE_ROW_RE.findall(html or ""):
        cells = re.findall(
            r'<td[^>]*class="([^"]*)"[^>]*>(.*?)</td>', row, re.I | re.S
        )
        rank_i: int | None = None
        num_i: int | None = None
        for cls, val in cells:
            text = _strip_html(val)
            if not text:
                continue
            if "Result_Num" in cls or re.search(r"\bRank\b", cls):
                try:
                    rank_i = int(re.search(r"\d+", text).group(0))  # type: ignore[union-attr]
                except Exception:
                    pass
            elif cls.strip() == "Num Txt_C" or (
                cls.startswith("Num ") and "Waku" not in cls and "Txt_C" in cls
            ):
                try:
                    num_i = int(re.search(r"\d+", text).group(0))  # type: ignore[union-attr]
                except Exception:
                    pass
        if rank_i is None or num_i is None:
            continue
        pairs.append((rank_i, num_i))
    pairs.sort(key=lambda x: x[0])
    return [n for _, n in pairs]


def parse_winner_name(html: str, finish_order: list[int]) -> str | None:
    if not finish_order:
        return None
    for row in _HORSE_ROW_RE.findall(html or ""):
        num_m = re.search(r'class="Num Txt_C"[^>]*>\s*(\d+)\s*<', row, re.I | re.S)
        if not num_m:
            continue
        try:
            if int(num_m.group(1)) != int(finish_order[0]):
                continue
        except ValueError:
            continue
        name_m = re.search(
            r'class="[^"]*Horse_Name[^"]*"[^>]*>.*?>([^<]+)<', row, re.I | re.S
        )
        if name_m:
            return _strip_html(name_m.group(1))
        # HorseNameSpan
        span = re.search(
            r'class="[^"]*HorseNameSpan[^"]*"[^>]*>([^<]+)<', row, re.I | re.S
        )
        if span:
            return _strip_html(span.group(1))
    return None


def _combo_key(nums: list[int], *, ordered: bool) -> str:
    xs = list(nums)
    if not ordered:
        xs = sorted(xs)
    return "-".join(str(x) for x in xs)


def parse_payouts(html: str) -> dict[str, dict[str, int]]:
    """
    JRA-style payouts: yen per ¥100.
    Keys: 単勝/複勝/馬連/ワイド/馬単/三連複/三連単 (+ 3連* aliases).
    """
    out: dict[str, dict[str, int]] = {}
    for body in _PAYOUT_TABLE_RE.findall(html or ""):
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.I | re.S):
            cells = [
                _strip_html(td)
                for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.I | re.S)
            ]
            cells = [c for c in cells if c]
            if len(cells) < 3:
                continue
            label = cells[0]
            nums_raw = cells[1]
            yen_raw = cells[2]
            yens = _parse_yen_list(yen_raw)
            nums = _parse_int_tokens(nums_raw)
            if not yens:
                continue
            if label == "単勝" and nums:
                out.setdefault("単勝", {})[str(nums[0])] = yens[0]
            elif label == "複勝":
                bucket = out.setdefault("複勝", {})
                for i, n in enumerate(nums[: len(yens)]):
                    bucket[str(n)] = yens[i]
            elif label == "枠連" and len(nums) >= 2:
                out.setdefault("枠連", {})[_combo_key(nums[:2], ordered=False)] = yens[0]
            elif label == "馬連" and len(nums) >= 2:
                out.setdefault("馬連", {})[_combo_key(nums[:2], ordered=False)] = yens[0]
            elif label == "馬単" and len(nums) >= 2:
                out.setdefault("馬単", {})[_combo_key(nums[:2], ordered=True)] = yens[0]
            elif label == "ワイド":
                bucket = out.setdefault("ワイド", {})
                # nums come as flat pairs: a b a b a b
                pairs = []
                for i in range(0, len(nums) - 1, 2):
                    pairs.append([nums[i], nums[i + 1]])
                for i, pair in enumerate(pairs[: len(yens)]):
                    bucket[_combo_key(pair, ordered=False)] = yens[i]
            elif label in ("3連複", "三連複") and len(nums) >= 3:
                key = _combo_key(nums[:3], ordered=False)
                out.setdefault("三連複", {})[key] = yens[0]
                out.setdefault("3連複", {})[key] = yens[0]
            elif label in ("3連単", "三連単") and len(nums) >= 3:
                key = _combo_key(nums[:3], ordered=True)
                out.setdefault("三連単", {})[key] = yens[0]
                out.setdefault("3連単", {})[key] = yens[0]
    return out


def parse_result_html(html: str) -> dict[str, Any] | None:
    finish_order = parse_finish_order(html)
    if len(finish_order) < 1:
        return None
    payouts = parse_payouts(html)
    winner_name = parse_winner_name(html, finish_order)
    return {
        "finish_order": finish_order,
        "payouts": payouts,
        "winner_horse_number": finish_order[0],
        "winner_name": winner_name,
        "field_size": len(finish_order),
        "finalized": True,
    }


class NetkeibaHttp:
    def __init__(
        self,
        *,
        timeout: float | None = None,
        min_interval_sec: float | None = None,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.timeout = float(
            timeout
            if timeout is not None
            else os.environ.get("EXPECT_NETKEIBA_TIMEOUT", "25")
        )
        self.min_interval = float(
            min_interval_sec
            if min_interval_sec is not None
            else os.environ.get("EXPECT_NETKEIBA_MIN_INTERVAL_SEC", "0.8")
        )
        self.user_agent = os.environ.get("EXPECT_NETKEIBA_USER_AGENT", DEFAULT_UA)
        self._last = 0.0
        self._opener = opener or urllib.request.urlopen

    def fetch(self, url: str) -> str:
        elapsed = time.monotonic() - self._last
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml",
                "Referer": "https://race.netkeiba.com/",
            },
            method="GET",
        )
        try:
            with self._opener(req, timeout=self.timeout) as resp:
                raw = resp.read()
                self._last = time.monotonic()
        except urllib.error.HTTPError as exc:
            raise NetkeibaResultError(f"HTTP {exc.code}: {url}") from exc
        except urllib.error.URLError as exc:
            raise NetkeibaResultError(f"URL error: {url}: {exc.reason}") from exc
        for enc in ("utf-8", "euc-jp", "cp932"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")

    def fetch_result_html(self, numeric_race_id: str) -> str:
        return self.fetch(RESULT_URL.format(race_id=numeric_race_id))


def fetch_pi_race_catalog(race_date: str) -> list[dict[str, Any]]:
    """PI GET /v1/races?date= → flat race list with race_id + numeric_race_id."""
    base = (
        os.environ.get("EXPECT_PI_BASE_URL")
        or os.environ.get("PI_BASE_URL")
        or "http://127.0.0.1:8081"
    ).rstrip("/")
    url = f"{base}/v1/races?date={race_date}"
    timeout = float(os.environ.get("EXPECT_PI_TIMEOUT", "20"))
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "Expect-ResultAutomation/7.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as exc:
        raise NetkeibaResultError(f"PI catalog failed: {exc}") from exc
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NetkeibaResultError("PI catalog JSON invalid") from exc
    # unwrap ok/data envelopes if present
    if isinstance(doc, dict) and "data" in doc and isinstance(doc["data"], dict):
        doc = doc["data"]
    races: list[dict[str, Any]] = []
    for venue in (doc.get("venues") or []):
        for race in (venue.get("races") or []):
            if isinstance(race, dict):
                races.append(race)
    if not races:
        # alternate shape: meetings[].races
        for meeting in (doc.get("meetings") or []):
            for race in (meeting.get("races") or []):
                if isinstance(race, dict):
                    races.append(race)
    return races


def pi_payload_to_bundle(pi_payload: dict[str, Any]) -> dict[str, Any] | None:
    """
    Map PI /v1/predictions/{id} payload → PredictionBundle-like dict
    (enough for Hit/Miss + Challenge axis/rivals). Does not change PE.
    """
    if not isinstance(pi_payload, dict):
        return None
    if pi_payload.get("prediction_available") is False:
        return None
    pred = pi_payload.get("prediction")
    if not isinstance(pred, dict):
        if pi_payload.get("evaluation"):
            return pi_payload
        return None
    candidates = pred.get("candidates") or []
    if not isinstance(candidates, list) or not candidates:
        return None

    mark_by_rank = {1: "honmei", 2: "taikou", 3: "ana", 4: "chuuken"}
    runners: list[dict[str, Any]] = []
    for c in candidates:
        if not isinstance(c, dict):
            continue
        try:
            rank = int(c.get("Rank") or c.get("rank") or c.get("model_rank") or 0)
        except (TypeError, ValueError):
            rank = 0
        try:
            hn = int(c.get("HorseNumber") or c.get("horse_number") or 0)
        except (TypeError, ValueError):
            hn = 0
        if hn < 1:
            continue
        name = (
            c.get("CandidateID")
            or c.get("horse_name")
            or c.get("HorseName")
            or ""
        )
        runners.append(
            {
                "candidate_id": f"c{hn:02d}",
                "horse_number": hn,
                "horse_name": name or None,
                "model_rank": rank or None,
                "win_prob": c.get("Confidence") or c.get("confidence"),
                "mark": mark_by_rank.get(rank, "none"),
            }
        )
    runners.sort(key=lambda r: int(r.get("model_rank") or 999))
    if not runners:
        return None

    race_id = str(pi_payload.get("race_id") or pred.get("race_id") or "")
    race_date = str(pi_payload.get("race_date") or pi_payload.get("date") or "")
    venue = str(pi_payload.get("venue") or pi_payload.get("course") or "")
    try:
        race_no = int(pi_payload.get("race_number") or pi_payload.get("race_no") or 0)
    except (TypeError, ValueError):
        race_no = 0
    overall = pred.get("overall_confidence")
    meta = pred.get("meta") if isinstance(pred.get("meta"), dict) else {}
    return {
        "schema_version": "single-prediction-bundle/2.0",
        "race_id": race_id,
        "race_info": {
            "race_id": race_id,
            "date": race_date,
            "venue": venue,
            "race_no": race_no or None,
            "race_name": pi_payload.get("race_name"),
        },
        "evaluation": {
            "status": "ok",
            "runners": runners,
            "world": pred.get("world"),
            "sub_world": pred.get("sub_world"),
        },
        "ai_confidence": {
            "status": "ok" if overall is not None else "unknown",
            "score": overall,
        },
        "explain": {"narrative": "", "meta": {"source": "pi-keibanet-api"}},
        "model_version": meta.get("model_version") or pred.get("core_version"),
        "prediction_version": "pi-mapped",
    }


def fetch_pi_prediction_bundle(race_id: str) -> dict[str, Any] | None:
    """Read-only PI prediction for Challenge / RA matching (no PE change)."""
    from urllib.parse import quote

    base = (
        os.environ.get("EXPECT_PI_BASE_URL")
        or os.environ.get("PI_BASE_URL")
        or "http://127.0.0.1:8081"
    ).rstrip("/")
    url = f"{base}/v1/predictions/{quote(race_id, safe='')}"
    timeout = float(os.environ.get("EXPECT_PI_TIMEOUT", "20"))
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "Expect-ResultAutomation/7.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        doc = json.loads(raw)
    except Exception:
        return None
    if isinstance(doc, dict) and doc.get("ok") is False:
        return None
    data = doc.get("data") if isinstance(doc, dict) else None
    payload = data if isinstance(data, dict) else doc
    if not isinstance(payload, dict):
        return None
    if payload.get("evaluation"):
        return payload
    return pi_payload_to_bundle(payload)
