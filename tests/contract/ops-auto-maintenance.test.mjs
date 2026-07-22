import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { ROOT } from "../helpers/load.mjs";

async function load(rel) {
  return import(pathToFileURL(join(ROOT, rel)).href);
}

/** JST の特定曜日に寄せた Date（UTC 固定） */
function jstWeekdayInstant(weekday /* 0=Sun … 6=Sat */) {
  // 2026-07-19 = Sun JST, 2026-07-20 = Mon, … 2026-07-25 = Sat
  const baseSun = Date.UTC(2026, 6, 19, 3, 0, 0); // ~12:00 JST Sun
  const day = weekday === 0 ? 0 : weekday;
  return new Date(baseSun + day * 86400000);
}

describe("V1.1 WeekendCalendarProvider", () => {
  it("土日は開催日、月〜金は非開催", async () => {
    const { decideWeekend } = await load(
      "functions/_lib/calendar/WeekendCalendarProvider.js"
    );
    assert.equal(decideWeekend(jstWeekdayInstant(6)).is_race_day, true); // Sat
    assert.equal(decideWeekend(jstWeekdayInstant(0)).is_race_day, true); // Sun
    assert.equal(decideWeekend(jstWeekdayInstant(1)).is_race_day, false); // Mon
    assert.equal(decideWeekend(jstWeekdayInstant(5)).is_race_day, false); // Fri
  });

  it("平日の next_open は次の土曜", async () => {
    const { decideWeekend } = await load(
      "functions/_lib/calendar/WeekendCalendarProvider.js"
    );
    const mon = decideWeekend(jstWeekdayInstant(1));
    assert.equal(mon.next_open_date_jst, "2026-07-25");
  });
});

describe("V1.1 resolveOpsModeDetailed auto maintenance", () => {
  it("Flag OFF では平日でも PUBLIC（現行同等）", async () => {
    const { resolveOpsModeDetailed, OpsMode } = await load("functions/_lib/opsMode.js");
    const r = await resolveOpsModeDetailed(
      { ui_features: { v11_auto_maintenance: false } },
      { now: jstWeekdayInstant(1) }
    );
    assert.equal(r.ops_mode, OpsMode.PUBLIC);
    assert.equal(r.reason, "default_public");
  });

  it("Flag ON + 平日 → CLOSED auto_calendar", async () => {
    const { resolveOpsModeDetailed, OpsMode } = await load("functions/_lib/opsMode.js");
    const r = await resolveOpsModeDetailed(
      { ui_features: { v11_auto_maintenance: true } },
      { now: jstWeekdayInstant(1) }
    );
    assert.equal(r.ops_mode, OpsMode.CLOSED);
    assert.equal(r.reason, "auto_calendar");
    assert.equal(r.manual_override, false);
  });

  it("Flag ON + 土曜 → PUBLIC", async () => {
    const { resolveOpsModeDetailed, OpsMode } = await load("functions/_lib/opsMode.js");
    const r = await resolveOpsModeDetailed(
      { ui_features: { v11_auto_maintenance: true } },
      { now: jstWeekdayInstant(6) }
    );
    assert.equal(r.ops_mode, OpsMode.PUBLIC);
    assert.equal(r.reason, "auto_calendar_race_day");
  });

  it("手動 ops_mode PUBLIC は平日でも最優先", async () => {
    const { resolveOpsModeDetailed, OpsMode } = await load("functions/_lib/opsMode.js");
    const r = await resolveOpsModeDetailed(
      {
        ops_mode: "PUBLIC",
        ui_features: { v11_auto_maintenance: true },
      },
      { now: jstWeekdayInstant(1) }
    );
    assert.equal(r.ops_mode, OpsMode.PUBLIC);
    assert.equal(r.reason, "manual_ops_mode");
    assert.equal(r.manual_override, true);
  });

  it("手動 maintenance_mode は土日でも CLOSED", async () => {
    const { resolveOpsModeDetailed, OpsMode } = await load("functions/_lib/opsMode.js");
    const r = await resolveOpsModeDetailed(
      {
        maintenance_mode: true,
        ui_features: { v11_auto_maintenance: true },
      },
      { now: jstWeekdayInstant(6) }
    );
    assert.equal(r.ops_mode, OpsMode.CLOSED);
    assert.equal(r.reason, "manual_maintenance_mode");
  });

  it("resolveOpsMode sync も Flag ON 平日で CLOSED", async () => {
    const { resolveOpsMode, OpsMode } = await load("functions/_lib/opsMode.js");
    assert.equal(
      resolveOpsMode(
        { ui_features: { v11_auto_maintenance: true } },
        { now: jstWeekdayInstant(3) }
      ),
      OpsMode.CLOSED
    );
    assert.equal(
      resolveOpsMode({ ui_features: { v11_auto_maintenance: false } }, { now: jstWeekdayInstant(3) }),
      OpsMode.PUBLIC
    );
  });

  it("stats heatmap は exempt（admin 平日確認用）", async () => {
    const { OpsMode, evaluateOpsAccess, OPS_MODE_EXEMPT_PATHS } = await load(
      "functions/_lib/opsMode.js"
    );
    assert.equal(OPS_MODE_EXEMPT_PATHS.has("/api/v1/stats/heatmap"), true);
    const r = evaluateOpsAccess({
      pathname: "/api/v1/stats/heatmap",
      opsMode: OpsMode.CLOSED,
      role: "USER",
    });
    assert.equal(r.allow, true);
    assert.equal(r.reason, "exempt_path");
  });

  it("public-status は exempt", async () => {
    const { OpsMode, evaluateOpsAccess, OPS_MODE_EXEMPT_PATHS } = await load(
      "functions/_lib/opsMode.js"
    );
    assert.equal(OPS_MODE_EXEMPT_PATHS.has("/api/ops/public-status"), true);
    const r = evaluateOpsAccess({
      pathname: "/api/ops/public-status",
      opsMode: OpsMode.CLOSED,
      role: "USER",
    });
    assert.equal(r.allow, true);
    assert.equal(r.reason, "exempt_path");
  });
});
