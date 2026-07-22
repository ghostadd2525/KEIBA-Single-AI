# -*- coding: utf-8 -*-
"""
Feature generation for runners_pace_market_features.csv.

Ported from demo_runners_history_features.py (Win5AI legacy).
All formulas are identical to the original — no new features.
"""
from __future__ import annotations

import math
import re
from typing import Any, Optional

import numpy as np
import pandas as pd


def _normalize(value: Any) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip().replace("\u3000", " ")
    s = re.sub(r"\s+", " ", s)
    return s


def _compact(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def _to_num(series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(v):
            return default
        s = str(v).strip().replace(",", "")
        if s in {"", "nan", "None", "---", "----", "--.-", "**"}:
            return default
        return float(s)
    except Exception:
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        if pd.isna(v):
            return default
        s = str(v).strip().replace(",", "")
        if s in {"", "nan", "None", "---", "----", "--.-", "**"}:
            return default
        return int(float(s))
    except Exception:
        return default


def _extract_corner_value(value, from_last: int = 1) -> float:
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    s = s.replace("−", "-").replace("ー", "-").replace("―", "-").replace("－", "-")
    s = s.replace("→", "-").replace("/", "-").replace(" ", "").replace("\u3000", "")
    nums = re.findall(r"\d+", s)
    pos = [int(x) for x in nums] if nums else []
    if not pos:
        return np.nan
    idx = -from_last
    if abs(idx) <= len(pos):
        return float(pos[idx])
    return np.nan


# --------------- Running style estimation (identical to legacy) ---------------

def _estimate_running_style(last3_avg_corner4, avg_corner4, front_rate, history_count):
    if pd.notna(last3_avg_corner4):
        x = float(last3_avg_corner4)
        if x <= 3.5:
            return "逃げ", 1.0, "corner4_last3"
        if x <= 6.5:
            return "先行", 1.0, "corner4_last3"
        if x <= 10.0:
            return "差し", 1.0, "corner4_last3"
        return "追込", 1.0, "corner4_last3"

    if pd.notna(avg_corner4):
        x = float(avg_corner4)
        if x <= 3.5:
            return "逃げ", 0.8, "corner4_all"
        if x <= 6.5:
            return "先行", 0.8, "corner4_all"
        if x <= 10.0:
            return "差し", 0.8, "corner4_all"
        return "追込", 0.8, "corner4_all"

    if history_count > 0:
        if pd.notna(front_rate):
            if float(front_rate) >= 0.55:
                return "先行", 0.4, "fallback_history"
            if float(front_rate) >= 0.25:
                return "差し", 0.3, "fallback_history"
        return "追込", 0.2, "fallback_history"

    return "追込", 0.0, "fallback_no_history"


def _sample_confidence(count: int, target: int = 3, floor: float = 0.60) -> float:
    if target <= 0:
        return 1.0
    c = max(0, int(count))
    if c >= target:
        return 1.0
    return round(float(floor + (1.0 - floor) * (c / target)), 6)


def _calc_history_score(history_count, style_confidence, avg_finish, last3_avg_finish, last_finish, layoff_penalty=0.0):
    score = 0.0
    if pd.notna(style_confidence):
        score += float(style_confidence) * 0.20
    if pd.notna(avg_finish):
        score += max(0.0, 1.0 - (float(avg_finish) - 1.0) / 18.0) * 0.08
    if pd.notna(last3_avg_finish):
        score += max(0.0, 1.0 - (float(last3_avg_finish) - 1.0) / 18.0) * 0.47
    if pd.notna(last_finish):
        score += max(0.0, 1.0 - (float(last_finish) - 1.0) / 18.0) * 0.25
    score = max(0.0, score - float(layoff_penalty))
    conf = _sample_confidence(history_count, 3, 0.60)
    return round(float(min(score, 1.0) * conf), 6)


def _calc_distance_score(sd_count, sd_avg, ss_count, ss_avg, history_count):
    score = 0.0
    if pd.notna(sd_count):
        score += min(float(sd_count), 5.0) / 5.0 * 0.18
    if pd.notna(sd_avg):
        score += max(0.0, 1.0 - (float(sd_avg) - 1.0) / 18.0) * 0.36
    if pd.notna(ss_count):
        score += min(float(ss_count), 5.0) / 5.0 * 0.08
    if pd.notna(ss_avg):
        score += max(0.0, 1.0 - (float(ss_avg) - 1.0) / 18.0) * 0.18
    c1 = _sample_confidence(min(_safe_int(sd_count, 0) + _safe_int(ss_count, 0), 3), 3, 0.62)
    c2 = _sample_confidence(history_count, 3, 0.60)
    return round(float(min(score, 1.0) * c1 * c2), 6)


# --------------- Grade points (identical to legacy) ---------------

def _grade_weight(race_name: str, race_class: str) -> tuple[float, str]:
    txt = f"{_normalize(race_name)} {_normalize(race_class)}".upper()
    if any(k in txt for k in ["JPN1", "ＧⅠ", "GⅠ", "GI", "JGI", "JPN I", "JPNI"]):
        return 1.00, "G1"
    if any(k in txt for k in ["JPN2", "ＧⅡ", "GⅡ", "GII", "JGII", "JPN II", "JPNII"]):
        return 0.74, "G2"
    if any(k in txt for k in ["JPN3", "ＧⅢ", "GⅢ", "GIII", "JGIII", "JPN III", "JPNIII"]):
        return 0.53, "G3"
    if any(k in txt for k in ["LISTED", "L ", "(L)", "L-"]):
        return 0.37, "L"
    if any(k in txt for k in ["OPEN", "OP", "オープン"]):
        return 0.31, "OP"
    if any(k in txt for k in ["3勝", "1600万", "3勝クラス"]):
        return 0.22, "3C"
    if any(k in txt for k in ["2勝", "1000万", "2勝クラス"]):
        return 0.135, "2C"
    if any(k in txt for k in ["1勝", "500万", "1勝クラス"]):
        return 0.09, "1C"
    if "未勝利" in txt:
        return 0.041, "MS"
    return 0.055, "OTHER"


def _finish_weight(finish) -> float:
    if pd.isna(finish):
        return 0.0
    x = float(finish)
    if x <= 1:
        return 1.00
    if x <= 2:
        return 0.62
    if x <= 3:
        return 0.36
    if x <= 5:
        return 0.16
    return 0.0


def _recency_weight(idx: int) -> float:
    if idx == 0:
        return 1.00
    if idx == 1:
        return 0.85
    if idx == 2:
        return 0.70
    return 0.0


def _distance_match_weight(hist_dist, target_dist) -> float:
    if pd.isna(hist_dist) or pd.isna(target_dist):
        return 0.70
    diff = abs(float(hist_dist) - float(target_dist))
    if diff <= 200:
        return 1.00
    if diff <= 400:
        return 0.80
    if diff <= 800:
        return 0.60
    return 0.45


def _running_style_fit_weight(style: str, target_distance) -> float:
    s = _normalize(style)
    if pd.isna(target_distance):
        return 0.80
    d = float(target_distance)
    if d >= 2800:
        if s in ["先行", "差し"]:
            return 1.00
        if s == "逃げ":
            return 0.75
        if s == "追込":
            return 0.90
        return 0.80
    if d >= 2200:
        if s in ["先行", "差し"]:
            return 0.95
        if s == "逃げ":
            return 0.85
        if s == "追込":
            return 0.90
        return 0.80
    if d >= 1800:
        if s in ["逃げ", "先行", "差し"]:
            return 0.90
        if s == "追込":
            return 0.80
        return 0.80
    if s in ["逃げ", "先行"]:
        return 0.95
    if s == "差し":
        return 0.85
    if s == "追込":
        return 0.70
    return 0.80


def _style_grade_bonus(race_name: str, style: str, target_distance) -> float:
    s = _normalize(style)
    d = float(target_distance) if pd.notna(target_distance) else np.nan
    name = _normalize(race_name)
    bonus = 0.0
    if pd.notna(d) and d >= 3000:
        if s == "先行":
            bonus += 0.10
        elif s == "差し":
            bonus += 0.08
        elif s == "追込":
            bonus += 0.05
        elif s == "逃げ":
            bonus -= 0.05
    if any(k in name for k in ["阪神大賞典", "天皇賞", "菊花賞", "ダイヤモンド"]):
        if s in ["先行", "差し"]:
            bonus += 0.08
    return bonus


def _squash(total: float) -> float:
    return float(1.0 - math.exp(-max(0.0, total)))


def _calc_last3_grade_points(last3: pd.DataFrame, target_dist, style: str, history_count: int) -> dict:
    raw_total = 0.0
    raw_stayer = 0.0
    raw_gds = 0.0
    style_fit_base = _running_style_fit_weight(style, target_dist)

    for idx, (_, r) in enumerate(last3.iterrows()):
        rn = r.get("history_race_name", "")
        rc = r.get("history_class", "")
        finish = r.get("history_finish", np.nan)
        hd = r.get("history_distance", np.nan)

        gw, _ = _grade_weight(rn, rc)
        fw = _finish_weight(finish)
        rw = _recency_weight(idx)
        dw = _distance_match_weight(hd, target_dist)

        point = gw * fw * rw
        raw_total += point
        if pd.notna(hd) and float(hd) >= 2400:
            raw_stayer += point
        sb = _style_grade_bonus(rn, style, target_dist)
        raw_gds += point * dw * style_fit_base + sb

    conf = _sample_confidence(history_count, 3, 0.60)
    return {
        "grade_points_last3_raw": round(raw_total, 6),
        "grade_points_last3": round(_squash(raw_total) * conf, 6),
        "stayer_grade_points_last3_raw": round(raw_stayer, 6),
        "stayer_grade_points_last3": round(_squash(raw_stayer) * conf, 6),
        "grade_distance_style_points_last3_raw": round(raw_gds, 6),
        "grade_distance_style_points_last3": round(_squash(raw_gds) * conf, 6),
        "style_distance_fit_weight": round(style_fit_base, 6),
        "grade_sample_confidence": conf,
    }


def _calc_layoff_days(runner_date, last_date) -> float:
    if pd.isna(runner_date) or pd.isna(last_date):
        return np.nan
    try:
        return float((pd.Timestamp(runner_date) - pd.Timestamp(last_date)).days)
    except Exception:
        return np.nan


def _calc_layoff_penalty(d) -> float:
    if pd.isna(d):
        return 0.0
    d = float(d)
    if d >= 180:
        return 0.10
    if d >= 140:
        return 0.07
    if d >= 84:
        return 0.045
    if d >= 49:
        return 0.020
    return 0.0


# --------------- Risk features (identical to legacy) ---------------

def _add_risk_features(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()

    if "gate" not in work.columns:
        for c in ["frame_number", "horse_number"]:
            if c in work.columns:
                work["gate"] = pd.to_numeric(work[c], errors="coerce").fillna(0)
                break
        if "gate" not in work.columns:
            work["gate"] = 0

    if "field_size" not in work.columns:
        if "race_id" in work.columns:
            work["field_size"] = work.groupby("race_id")["race_id"].transform("size")
        else:
            work["field_size"] = len(work)

    for col in ["running_style", "last3_avg_corner4", "last3_avg_finish"]:
        if col not in work.columns:
            work[col] = 0

    denom = (pd.to_numeric(work["field_size"], errors="coerce").fillna(0) + 1).replace(0, 1)
    work["gate_risk_score"] = (
        (pd.to_numeric(work["last3_avg_corner4"], errors="coerce").fillna(0) / denom) * 0.6
        + (1.0 - pd.to_numeric(work["last3_avg_finish"], errors="coerce").fillna(0) / denom) * 0.4
    )

    work["inside_traffic_risk"] = 0.0
    is_inside = pd.to_numeric(work["gate"], errors="coerce").fillna(99) <= 3
    is_sashi = work["running_style"].isin(["差し", "追込"])
    work.loc[is_inside & is_sashi, "inside_traffic_risk"] = 0.6
    work.loc[pd.to_numeric(work["field_size"], errors="coerce").fillna(0) >= 14, "inside_traffic_risk"] += 0.2

    work["style_disadvantage_score"] = 0.0
    work.loc[work["running_style"] == "差し", "style_disadvantage_score"] = 0.2
    work.loc[work["running_style"] == "追込", "style_disadvantage_score"] = 0.35

    style_norm = work["running_style"].fillna("").astype(str).str.strip()
    work["is_nige"] = (style_norm == "逃げ").astype(int)
    work["is_senkou"] = (style_norm == "先行").astype(int)
    work["is_sashi_flag"] = (style_norm == "差し").astype(int)
    work["is_oikomi"] = style_norm.isin(["追込", "追い込み"]).astype(int)

    if "race_id" in work.columns:
        race_key = work["race_id"].astype(str)
        work["nige_count"] = work.groupby(race_key)["is_nige"].transform("sum")
        work["senkou_count"] = work.groupby(race_key)["is_senkou"].transform("sum")
        work["sashi_count"] = work.groupby(race_key)["is_sashi_flag"].transform("sum")
        work["oikomi_count"] = work.groupby(race_key)["is_oikomi"].transform("sum")
    else:
        work["nige_count"] = int(work["is_nige"].sum())
        work["senkou_count"] = int(work["is_senkou"].sum())
        work["sashi_count"] = int(work["is_sashi_flag"].sum())
        work["oikomi_count"] = int(work["is_oikomi"].sum())

    work["pace_pressure"] = (
        pd.to_numeric(work["nige_count"], errors="coerce").fillna(0.0) * 1.2
        + pd.to_numeric(work["senkou_count"], errors="coerce").fillna(0.0) * 0.8
    )
    work["pace_pressure_rate"] = work["pace_pressure"] / pd.to_numeric(work["field_size"], errors="coerce").fillna(0).clip(lower=1)

    work["pace_collapse_risk_v2"] = 0.0
    if "race_id" in work.columns:
        for race_id, group in work.groupby("race_id"):
            nige = pd.to_numeric(group["nige_count"], errors="coerce").fillna(0).iloc[0]
            senko = pd.to_numeric(group["senkou_count"], errors="coerce").fillna(0).iloc[0]
            total = len(group)
            pace = ((nige * 0.6) + (senko * 0.4)) / max(total, 1)
            entropy_like = 0.5
            risk = pace * 0.7 + entropy_like * 0.3
            work.loc[group.index, "pace_collapse_risk_v2"] = risk

    for col in ["gate_risk_score", "inside_traffic_risk", "style_disadvantage_score", "pace_collapse_risk_v2"]:
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0).clip(0.0, 1.0)

    work.drop(columns=["is_nige", "is_senkou", "is_sashi_flag", "is_oikomi"], inplace=True, errors="ignore")

    return work


def _attach_win5_leg_from_races(df: pd.DataFrame) -> pd.DataFrame:
    """Assign win5_leg using the same rule as demo_pace_model_v2.py."""
    out = df.copy()
    if "win5_leg" in out.columns and out["win5_leg"].notna().any():
        return out
    if "win5_leg" not in out.columns:
        out["win5_leg"] = pd.NA
    if "race_id" not in out.columns or "date" not in out.columns:
        return out

    races = out.drop_duplicates(subset=["race_id"], keep="first").copy()
    races["_leg_date"] = pd.to_datetime(races["date"], errors="coerce")
    if "race_number" in races.columns:
        races["_leg_rno"] = pd.to_numeric(races["race_number"], errors="coerce")
        races = races.sort_values(["_leg_date", "_leg_rno", "race_id"], kind="stable")
    else:
        races = races.sort_values(["_leg_date", "race_id"], kind="stable")
    races["win5_leg"] = races.groupby("_leg_date", dropna=False).cumcount() + 1
    leg_map = races[["race_id", "win5_leg"]]
    out = out.merge(leg_map, on="race_id", how="left", suffixes=("", "_assigned"))
    if "win5_leg_assigned" in out.columns:
        out["win5_leg"] = out["win5_leg_assigned"]
        out.drop(columns=["win5_leg_assigned"], inplace=True)
    return out


# --------------- Main entry point ---------------

def build_features(
    runners_df: pd.DataFrame,
    history_df: pd.DataFrame,
    races_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Build runners_pace_market_features from runners + horse_history_raw.

    Input/output schema matches Win5AI legacy exactly.
    """
    runners = runners_df.copy()
    hist = history_df.copy()

    runners["horse_id"] = runners["horse_id"].astype(str).str.strip()
    if "race_id" in runners.columns:
        runners["race_id"] = runners["race_id"].astype(str).str.strip()

    hist["horse_id"] = hist["horse_id"].astype(str).str.strip()
    if "race_id" in hist.columns:
        hist["race_id"] = hist["race_id"].astype(str).str.strip()

    # Merge race context if available
    if races_df is not None and "race_id" in races_df.columns:
        race_cols = [c for c in [
            "race_id", "numeric_race_id", "date", "course", "race_number", "race_name",
            "target_surface", "target_distance", "turn", "weather", "track_condition",
            "win5_leg", "race_label",
        ] if c in races_df.columns]
        if len(race_cols) > 1:
            right = races_df[race_cols].copy()
            right["race_id"] = right["race_id"].astype(str).str.strip()
            runners = runners.merge(right, on="race_id", how="left", suffixes=("", "_race"))

    # Date columns
    runner_date_col = None
    for c in ["date", "race_date", "result_date"]:
        if c in runners.columns:
            runner_date_col = c
            break
    history_date_col = None
    for c in ["history_date", "past_date", "prev_date", "date", "race_date"]:
        if c in hist.columns:
            history_date_col = c
            break

    runners["_runner_date_dt"] = pd.to_datetime(runners[runner_date_col], errors="coerce") if runner_date_col else pd.NaT
    hist["_history_date_dt"] = pd.to_datetime(hist[history_date_col], errors="coerce") if history_date_col else pd.NaT

    # Ensure standard columns in hist
    hist["history_finish"] = _to_num(hist.get("history_finish", np.nan))
    if "corner4" not in hist.columns:
        hist["corner4"] = hist.get("history_passing", pd.Series(dtype="object")).apply(lambda x: _extract_corner_value(x, 1))
    hist["corner4"] = _to_num(hist["corner4"])
    hist["history_distance"] = _to_num(hist.get("history_distance", np.nan))
    hist["history_surface"] = hist.get("history_surface", "unknown").astype(str)
    hist["history_race_name"] = hist.get("history_race_name", "").astype(str)
    hist["history_class"] = hist.get("history_class", "").astype(str)

    out_rows = []
    for _, row in runners.iterrows():
        horse_id = str(row["horse_id"]).strip()
        runner_date = row["_runner_date_dt"]

        h = hist[hist["horse_id"] == horse_id].copy()
        if pd.notna(runner_date) and "_history_date_dt" in h.columns:
            h = h[h["_history_date_dt"] < runner_date]
        h = h.sort_values("_history_date_dt", ascending=False, na_position="last")

        history_count = len(h)
        corner4_count = int(h["corner4"].notna().sum()) if "corner4" in h.columns else 0

        last1 = h.head(1)
        last3 = h.head(3)

        last_finish = last1["history_finish"].iloc[0] if len(last1) > 0 else np.nan
        last3_avg_finish = last3["history_finish"].mean() if len(last3) > 0 else np.nan
        avg_finish = h["history_finish"].mean() if history_count > 0 else np.nan

        last3_avg_corner4 = last3["corner4"].mean() if len(last3) > 0 else np.nan
        avg_corner4 = h["corner4"].mean() if corner4_count > 0 else np.nan
        front_rate = float((h["corner4"] <= 4).mean()) if corner4_count > 0 else np.nan

        running_style, style_confidence, style_source = _estimate_running_style(
            last3_avg_corner4, avg_corner4, front_rate, history_count,
        )

        target_distance = _to_num(pd.Series([row.get("target_distance", np.nan)])).iloc[0]
        target_surface = str(row.get("target_surface", "unknown"))

        if pd.notna(target_distance):
            same_dist = h[np.abs(_to_num(h["history_distance"]) - target_distance) <= 200]
        else:
            same_dist = h.iloc[0:0]
        same_surf = h[h["history_surface"].astype(str) == target_surface]

        sd_count = len(same_dist)
        sd_avg = same_dist["history_finish"].mean() if sd_count > 0 else np.nan
        ss_count = len(same_surf)
        ss_avg = same_surf["history_finish"].mean() if ss_count > 0 else np.nan

        grade_pts = _calc_last3_grade_points(last3, target_distance, running_style, history_count)

        last_hdate = last1["_history_date_dt"].iloc[0] if len(last1) > 0 else pd.NaT
        layoff_days = _calc_layoff_days(runner_date, last_hdate)
        layoff_penalty = _calc_layoff_penalty(layoff_days)

        history_score = _calc_history_score(
            history_count, style_confidence, avg_finish, last3_avg_finish, last_finish, layoff_penalty,
        )
        distance_score = _calc_distance_score(sd_count, sd_avg, ss_count, ss_avg, history_count)

        out = row.to_dict()
        out.update({
            "history_count": history_count,
            "history_confidence": round(_sample_confidence(history_count, 3, 0.60), 6),
            "layoff_days": layoff_days,
            "layoff_penalty": layoff_penalty,
            "last_finish": last_finish,
            "last3_avg_finish": last3_avg_finish,
            "avg_finish": avg_finish,
            "corner4_count": corner4_count,
            "last3_avg_corner4": last3_avg_corner4,
            "avg_corner4": avg_corner4,
            "front_rate": front_rate,
            "running_style": running_style,
            "style_confidence": style_confidence,
            "style_source": style_source,
            "same_distance_count": sd_count,
            "same_distance_avg_finish": sd_avg,
            "same_surface_count": ss_count,
            "same_surface_avg_finish": ss_avg,
            "distance_score": distance_score,
            "history_score": history_score,
            "corner4_restored_flag": int(corner4_count > 0),
            "used_history_date_col": history_date_col or "",
            **grade_pts,
        })
        out_rows.append(out)

    out_df = pd.DataFrame(out_rows)
    out_df = _add_risk_features(out_df)

    if "win5_leg" not in out_df.columns:
        out_df["win5_leg"] = pd.NA
    if "race_label" not in out_df.columns:
        out_df["race_label"] = pd.NA
    # Win5AI legacy output uses race_id as race_label (race_name is not in final schema).
    if "race_id" in out_df.columns:
        out_df["race_label"] = out_df["race_label"].fillna(out_df["race_id"])
    elif "race_name" in out_df.columns:
        out_df["race_label"] = out_df["race_label"].fillna(out_df["race_name"])

    out_df = _attach_win5_leg_from_races(out_df)

    # Drop internal columns
    for c in ["_runner_date_dt"]:
        if c in out_df.columns:
            out_df.drop(columns=[c], inplace=True)

    return out_df
