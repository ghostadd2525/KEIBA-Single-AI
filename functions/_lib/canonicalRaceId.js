/**
 * Canonical race-id helpers (PROD-ALL-RACE-04 / P0-1).
 * Canonical form: YYYY-MM-DD-{venue}-{RR:02d}
 * Meeting-index (YYYY-MM-DD-NN-RR) is NEVER treated as JRA venue code.
 */
const CATALOG_RE = /^(\d{4}-\d{2}-\d{2})-([\u4e00-\u9fff]+)-(\d{1,2})$/;
const WIN5_RE = /^(\d{4}-\d{2}-\d{2})-(\d{2})-(\d{1,2})$/;
const SLUG_RE = /^(\d{8})_([a-z0-9]+)_(\d+)$/i;

const VENUE_EN_TO_JA = {
  sapporo: "札幌",
  hakodate: "函館",
  fukushima: "福島",
  niigata: "新潟",
  tokyo: "東京",
  nakayama: "中山",
  chukyo: "中京",
  kyoto: "京都",
  hanshin: "阪神",
  kokura: "小倉",
};

export function makeCanonical(date, venue, raceNo) {
  const d = String(date || "").trim();
  const v = String(venue || "").trim();
  const n = Number(raceNo);
  if (!d || !v || !Number.isFinite(n) || n <= 0) return null;
  return `${d}-${v}-${String(Math.trunc(n)).padStart(2, "0")}`;
}

export function isMeetingIndexId(raceId) {
  return WIN5_RE.test(String(raceId || "").trim());
}

export function isCatalogVenueId(raceId) {
  return CATALOG_RE.test(String(raceId || "").trim());
}

/**
 * Local normalize when venue is already known (no JRA meeting confusion).
 * @returns {{ canonical_race_id: string|null, source_race_id: string, date?: string, venue?: string, race_number?: number, format: string }}
 */
export function normalizeRaceIdLocal(raceId) {
  const raw = String(raceId || "").trim();
  const out = {
    canonical_race_id: null,
    source_race_id: raw,
    format: "unknown",
  };
  if (!raw) return out;

  let m = CATALOG_RE.exec(raw);
  if (m) {
    out.date = m[1];
    out.venue = m[2];
    out.race_number = Number(m[3]);
    out.canonical_race_id = makeCanonical(out.date, out.venue, out.race_number);
    out.format = "catalog";
    return out;
  }

  m = WIN5_RE.exec(raw);
  if (m) {
    out.date = m[1];
    out.meeting_label = Number(m[2]);
    out.race_number = Number(m[3]);
    out.format = "win5_meeting";
    // Venue unknown without day meeting map — caller must resolve via AI / catalog.
    return out;
  }

  m = SLUG_RE.exec(raw);
  if (m) {
    const ymd = m[1];
    out.date = `${ymd.slice(0, 4)}-${ymd.slice(4, 6)}-${ymd.slice(6, 8)}`;
    out.venue = VENUE_EN_TO_JA[String(m[2]).toLowerCase()] || m[2];
    out.race_number = Number(m[3]);
    out.canonical_race_id = makeCanonical(out.date, out.venue, out.race_number);
    out.format = "slug";
    return out;
  }

  return out;
}

/**
 * Prefer AI /v1/races/resolve (fixed RaceResolver). Falls back to local parse.
 */
export async function resolveCanonicalRaceRef(aiFetchFn, context, raceId) {
  const local = normalizeRaceIdLocal(raceId);
  if (local.canonical_race_id && local.format !== "win5_meeting") {
    return {
      ...local,
      core_race_id: local.canonical_race_id,
      resolved_via: "local",
    };
  }

  if (typeof aiFetchFn !== "function") {
    return { ...local, resolved_via: "local_incomplete" };
  }

  try {
    const proxied = await aiFetchFn(
      context,
      `/v1/races/resolve?q=${encodeURIComponent(String(raceId || "").trim())}`,
      { timeoutMs: 8000 }
    );
    if (!proxied || proxied instanceof Response || !proxied.ok) {
      return { ...local, resolved_via: "ai_resolve_failed" };
    }
    const data = proxied.payload?.data != null ? proxied.payload.data : proxied.payload;
    if (!data || typeof data !== "object") {
      return { ...local, resolved_via: "ai_resolve_empty" };
    }
    const venue = data.venue || data.venue_ja;
    const raceNo = data.race_no ?? data.race_number;
    const canonical =
      data.canonical_race_id ||
      data.catalog_race_id ||
      makeCanonical(data.date, venue, raceNo);
    return {
      canonical_race_id: canonical || null,
      source_race_id: String(raceId || "").trim(),
      core_race_id: data.core_race_id || null,
      public_race_id: data.public_race_id || null,
      catalog_race_id: data.catalog_race_id || null,
      date: data.date,
      venue,
      race_number: raceNo,
      format: local.format,
      resolved_via: "ai_resolve",
      raw: data,
    };
  } catch {
    return { ...local, resolved_via: "ai_resolve_exception" };
  }
}
