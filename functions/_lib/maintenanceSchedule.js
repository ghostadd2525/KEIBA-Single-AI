/**
 * Version7 Maintenance Mode — Research Week schedule (JST).
 *
 * Maintenance window (CLOSED for general users):
 *   Sunday 21:00 JST  ≤  t  <  Saturday 00:00 JST
 *
 * Public window:
 *   Saturday 00:00 JST  ≤  t  <  Sunday 21:00 JST
 *
 * Server is source of truth. PE / CE / AI untouched.
 * ADMIN / OPS / DEVELOPER bypass CLOSED via roles (JWT kept; no force logout).
 */

const TZ = "Asia/Tokyo";

/**
 * @param {Date} [now]
 * @returns {{
 *   year: number, month: number, day: number,
 *   weekday: number, hour: number, minute: number, second: number,
 *   date_jst: string, time_jst: string
 * }}
 * weekday: 0=Sun … 6=Sat (JST)
 */
export function getJstParts(now = new Date()) {
  const d = now instanceof Date ? now : new Date(now);
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const map = {};
  for (const p of fmt.formatToParts(d)) {
    if (p.type !== "literal") map[p.type] = p.value;
  }
  const wdMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  const weekday = wdMap[map.weekday] ?? 0;
  let hour = Number(map.hour);
  // en-US hour12:false can yield "24" for midnight in some engines
  if (hour === 24) hour = 0;
  const year = Number(map.year);
  const month = Number(map.month);
  const day = Number(map.day);
  const minute = Number(map.minute);
  const second = Number(map.second);
  return {
    year,
    month,
    day,
    weekday,
    hour,
    minute,
    second,
    date_jst: `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
    time_jst: `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:${String(second).padStart(2, "0")}`,
  };
}

/**
 * @param {Date} [now]
 * @returns {boolean}
 */
export function isResearchWeekMaintenance(now = new Date()) {
  const p = getJstParts(now);
  const mins = p.hour * 60 + p.minute;
  // Sun 21:00 inclusive → maintenance
  if (p.weekday === 0) return mins >= 21 * 60;
  // Mon–Fri → maintenance (entire day until Sat 00:00)
  if (p.weekday >= 1 && p.weekday <= 5) return true;
  // Sat 00:00+ → public
  if (p.weekday === 6) return false;
  return false;
}

/**
 * Build ISO-like JST wall timestamps for current / next window.
 * @param {Date} [now]
 */
export function resolveMaintenanceWindow(now = new Date()) {
  const p = getJstParts(now);
  const maintenance = isResearchWeekMaintenance(now);

  if (maintenance) {
    const start = mostRecentSunday21Jst(p);
    const end = upcomingSaturday00Jst(p);
    return {
      maintenance: true,
      maintenance_start: start,
      maintenance_end: end,
      reason: "Research Week",
      date_jst: p.date_jst,
      time_jst: p.time_jst,
    };
  }

  const start = upcomingSunday21Jst(p);
  const end = saturday00AfterSunday21(start);
  return {
    maintenance: false,
    maintenance_start: start,
    maintenance_end: end,
    reason: "Production Open",
    date_jst: p.date_jst,
    time_jst: p.time_jst,
  };
}

function pad2(n) {
  return String(n).padStart(2, "0");
}

/** Format as `YYYY-MM-DDTHH:mm:ss+09:00` */
function jstIso(y, m, d, hh, mm, ss = 0) {
  return `${y}-${pad2(m)}-${pad2(d)}T${pad2(hh)}:${pad2(mm)}:${pad2(ss)}+09:00`;
}

function addDaysYmd(y, m, d, delta) {
  const utc = Date.UTC(y, m - 1, d + delta);
  const dt = new Date(utc);
  return {
    y: dt.getUTCFullYear(),
    m: dt.getUTCMonth() + 1,
    d: dt.getUTCDate(),
  };
}

/** Most recent Sunday 21:00 JST on or before `p` (when in maintenance). */
function mostRecentSunday21Jst(p) {
  if (p.weekday === 0) {
    return jstIso(p.year, p.month, p.day, 21, 0, 0);
  }
  // Mon=1 … Fri=5 → go back weekday days to Sunday
  const back = p.weekday;
  const s = addDaysYmd(p.year, p.month, p.day, -back);
  return jstIso(s.y, s.m, s.d, 21, 0, 0);
}

/** Upcoming Saturday 00:00 JST after current maintenance start. */
function upcomingSaturday00Jst(p) {
  // Days until Saturday (6): Sun=0 → 6, Mon=1 → 5, … Fri=5 → 1
  if (p.weekday === 6) {
    return jstIso(p.year, p.month, p.day, 0, 0, 0);
  }
  const ahead = 6 - p.weekday;
  const s = addDaysYmd(p.year, p.month, p.day, ahead);
  return jstIso(s.y, s.m, s.d, 0, 0, 0);
}

function upcomingSunday21Jst(p) {
  if (p.weekday === 0 && p.hour * 60 + p.minute < 21 * 60) {
    return jstIso(p.year, p.month, p.day, 21, 0, 0);
  }
  const ahead = (7 - p.weekday) % 7 || 7;
  const s = addDaysYmd(p.year, p.month, p.day, ahead);
  return jstIso(s.y, s.m, s.d, 21, 0, 0);
}

function saturday00AfterSunday21(sunday21Iso) {
  const m = String(sunday21Iso).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return sunday21Iso;
  const s = addDaysYmd(Number(m[1]), Number(m[2]), Number(m[3]), 6);
  return jstIso(s.y, s.m, s.d, 0, 0, 0);
}

/**
 * Human message for UI / 503.
 */
export function maintenanceUserMessage(beta) {
  if (beta && beta.maintenance_message) return String(beta.maintenance_message);
  return "ただいまメンテナンス中です（Research Week）。土曜 0:00（JST）以降に再度ログインしてください。";
}
