# -*- coding: utf-8 -*-
"""Phase1 Horse Intelligence — profile + pedigree from db.netkeiba."""
from __future__ import annotations

import json
import os
import re
from html import unescape
from typing import Any

from ..anti_leak import accept_observation, anti_leak_ok
from .netkeiba_client import ResearchNetkeibaClient, ResearchNetkeibaError


def _asof_enabled() -> bool:
    raw = (os.environ.get("RESEARCH_HARVEST_ASOF") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _strip(s: str) -> str:
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


def parse_horse_profile(html: str) -> dict[str, str | None]:
    out: dict[str, str | None] = {
        "breeder": None,
        "owner": None,
        "sale_price": None,
        "trainer": None,
    }
    mapping = {
        "生産者": "breeder",
        "馬主": "owner",
        "セリ取引価格": "sale_price",
        "調教師": "trainer",
    }
    for th, key in mapping.items():
        m = re.search(
            rf"<th[^>]*>\s*{re.escape(th)}\s*</th>\s*<td[^>]*>(.*?)</td>",
            html,
            re.S,
        )
        if not m:
            continue
        val = _strip(m.group(1))
        if not val or val in ("-", "—", "－"):
            out[key] = None if key == "sale_price" else (None if not val else val)
            if key == "sale_price":
                out[key] = None  # missing allowed
            continue
        if key == "sale_price" and val in ("-", "—", "－"):
            out[key] = None
        else:
            out[key] = val
    return out


def parse_pedigree_ajax(raw: str) -> dict[str, str | None]:
    """Parse ajax_horse_pedigree HTML or JSON{status,data} → sire/dam/damsire."""
    frag = raw
    text = raw.strip()
    if text.startswith("{"):
        try:
            j = json.loads(text)
            frag = j.get("data") or ""
        except Exception:
            frag = raw

    m = re.search(
        r'<table[^>]*class="blood_table"[^>]*>(.*?)</table>',
        frag,
        re.S | re.I,
    )
    if not m:
        return {"sire": None, "dam": None, "damsire": None}

    cells: list[tuple[str, int, str]] = []
    for cm in re.finditer(r"<td([^>]*)>(.*?)</td>", m.group(1), re.S | re.I):
        attrs, inner = cm.group(1), cm.group(2)
        cls = (re.search(r'class="([^"]*)"', attrs) or [None, ""])[1] or ""
        rs = int((re.search(r'rowspan="(\d+)"', attrs) or [None, "1"])[1] or "1")
        nm = re.search(r"<span[^>]*>([^<]*)</span>", inner)
        name = _strip(nm.group(1) if nm else inner)
        if name:
            cells.append((cls, rs, name))

    sire = next((n for c, rs, n in cells if "b_ml" in c and rs >= 2), None)
    dam = next((n for c, rs, n in cells if "b_fml" in c and rs >= 2), None)
    damsire = None
    seen_dam = False
    for c, rs, n in cells:
        if dam and n == dam and "b_fml" in c and rs >= 2:
            seen_dam = True
            continue
        if seen_dam and "b_ml" in c:
            damsire = n
            break
    return {"sire": sire, "dam": dam, "damsire": damsire}


def collect_horse_intelligence(
    *,
    runners: list[dict[str, Any]],
    prediction_created_at: str,
    fetched_at: str,
    client: ResearchNetkeibaClient | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """
    Enrich runners with sire/damsire/breeder/owner/sale_price.
    Requires runners[*].horse_id when available.
    """
    nk = client or ResearchNetkeibaClient()
    observed_at = prediction_created_at if _asof_enabled() else fetched_at
    if not anti_leak_ok(observed_at=observed_at, prediction_created_at=prediction_created_at):
        observed_at = prediction_created_at

    cache: dict[str, dict[str, Any]] = {}
    violations = 0
    profile_ok = 0
    pedigree_ok = 0
    profile_attempts = 0
    pedigree_attempts = 0

    for row in runners:
        hid = str(row.get("horse_id") or "").strip()
        if not hid:
            for fid in ("sire", "damsire", "breeder", "owner", "sale_price"):
                row.setdefault(fid, None)
                row.setdefault("missing", []).append(
                    {
                        "field": fid,
                        "reason": "horse_id_missing",
                        "source_id": "netkeiba_horse_db",
                    }
                )
            continue

        if hid not in cache:
            cache[hid] = {
                "sire": None,
                "damsire": None,
                "breeder": None,
                "owner": None,
                "sale_price": None,
                "errors": [],
            }
            # Profile
            profile_attempts += 1
            try:
                html = nk.fetch_horse_profile(hid)
                prof = parse_horse_profile(html)
                for k in ("breeder", "owner", "sale_price"):
                    cache[hid][k] = prof.get(k)
                if any(prof.get(k) for k in ("breeder", "owner", "sale_price")):
                    profile_ok += 1
            except ResearchNetkeibaError as exc:
                cache[hid]["errors"].append(f"profile:{exc}")

            # Pedigree AJAX
            pedigree_attempts += 1
            try:
                raw = nk.fetch_horse_pedigree_ajax(hid)
                ped = parse_pedigree_ajax(raw)
                cache[hid]["sire"] = ped.get("sire")
                cache[hid]["damsire"] = ped.get("damsire")
                if ped.get("sire") or ped.get("damsire"):
                    pedigree_ok += 1
            except ResearchNetkeibaError as exc:
                cache[hid]["errors"].append(f"pedigree:{exc}")

        data = cache[hid]
        for fid in ("sire", "damsire", "breeder", "owner", "sale_price"):
            raw_val = data.get(fid)
            # sale_price missing is allowed (None without error if parse found '-')
            val, _, miss = accept_observation(
                value=raw_val,
                observed_at=observed_at,
                prediction_created_at=prediction_created_at,
            )
            if miss == "anti_leak_rejected":
                violations += 1
            if val is not None:
                row[fid] = val
            else:
                row[fid] = None
                reason = miss or (
                    "not_listed"
                    if fid == "sale_price"
                    else (
                        "fetch_failed"
                        if data.get("errors")
                        else "parse_failed"
                    )
                )
                if fid == "sale_price" and raw_val is None and not data.get("errors"):
                    reason = "not_listed"
                row.setdefault("missing", []).append(
                    {
                        "field": fid,
                        "reason": reason,
                        "source_id": (
                            "netkeiba_pedigree_ajax"
                            if fid in ("sire", "damsire")
                            else "netkeiba_horse_db"
                        ),
                    }
                )

    sources = [
        {
            "feature_id": "horse_profile",
            "source_id": "netkeiba_horse_db",
            "success": profile_ok > 0,
            "observed_at": observed_at,
            "fetched_at": fetched_at,
            "asof_clamped": _asof_enabled(),
            "meta": {
                "attempts": profile_attempts,
                "ok": profile_ok,
                "unique_horses": len(cache),
            },
        },
        {
            "feature_id": "pedigree",
            "source_id": "netkeiba_pedigree_ajax",
            "success": pedigree_ok > 0,
            "observed_at": observed_at,
            "fetched_at": fetched_at,
            "asof_clamped": _asof_enabled(),
            "meta": {
                "attempts": pedigree_attempts,
                "ok": pedigree_ok,
                "unique_horses": len(cache),
            },
        },
    ]
    return runners, sources, violations
