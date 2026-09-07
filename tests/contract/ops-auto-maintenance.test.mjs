import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { ROOT } from "../helpers/load.mjs";

async function load(rel) {
  return import(pathToFileURL(join(ROOT, rel)).href);
}

/** JST の特定曜日 12:00 付近（UTC 固定） */
function jstWeekdayInstant(weekday /* 0=Sun … 6=Sat */) {
  const baseSun = Date.UTC(2026, 6, 19, 3, 0, 0); // ~12:00 JST Sun
  return new Date(baseSun + weekday * 86400000);
}

/** JST wall clock → Date */
function jstWall(y, m, d, hh, mm) {
  return new Date(Date.UTC(y, m - 1, d, hh - 9, mm, 0));
}

describe("V7 Research Week maintenance schedule (Sat 00:00 end)", () => {
  it("日曜 20:59 → 公開、21:00 → メンテ", async () => {
    const { isResearchWeekMaintenance } = await load(
      "functions/_lib/maintenanceSchedule.js"
    );
    assert.equal(isResearchWeekMaintenance(jstWall(2026, 7, 19, 20, 59)), false);
    assert.equal(isResearchWeekMaintenance(jstWall(2026, 7, 19, 21, 0)), true);
  });

  it("月〜金はメンテ、土曜 0:00 以降は公開", async () => {
    const { isResearchWeekMaintenance } = await load(
      "functions/_lib/maintenanceSchedule.js"
    );
    assert.equal(isResearchWeekMaintenance(jstWeekdayInstant(1)), true); // Mon
    assert.equal(isResearchWeekMaintenance(jstWeekdayInstant(4)), true); // Thu
    assert.equal(isResearchWeekMaintenance(jstWeekdayInstant(5)), true); // Fri noon
    assert.equal(isResearchWeekMaintenance(jstWall(2026, 7, 24, 23, 59)), true); // Fri 23:59
    assert.equal(isResearchWeekMaintenance(jstWall(2026, 7, 25, 0, 0)), false); // Sat 00:00
    assert.equal(isResearchWeekMaintenance(jstWeekdayInstant(6)), false); // Sat noon
  });

  it("window end は土曜 00:00", async () => {
    const { resolveMaintenanceWindow } = await load(
      "functions/_lib/maintenanceSchedule.js"
    );
    const w = resolveMaintenanceWindow(jstWall(2026, 7, 20, 12, 0)); // Mon
    assert.equal(w.maintenance, true);
    assert.equal(w.reason, "Research Week");
    assert.match(w.maintenance_start, /T21:00:00\+09:00$/);
    assert.match(w.maintenance_end, /T00:00:00\+09:00$/);
    assert.match(w.maintenance_end, /2026-07-25T00:00:00\+09:00/);
  });
});

describe("V1.1 WeekendCalendarProvider (unchanged)", () => {
  it("土日は開催日、月〜金は非開催", async () => {
    const { decideWeekend } = await load(
      "functions/_lib/calendar/WeekendCalendarProvider.js"
    );
    assert.equal(decideWeekend(jstWeekdayInstant(6)).is_race_day, true);
    assert.equal(decideWeekend(jstWeekdayInstant(0)).is_race_day, true);
    assert.equal(decideWeekend(jstWeekdayInstant(1)).is_race_day, false);
    assert.equal(decideWeekend(jstWeekdayInstant(5)).is_race_day, false);
  });
});

describe("V7 resolveOpsModeDetailed Research Week", () => {
  it("Flag OFF では平日でも PUBLIC", async () => {
    const { resolveOpsModeDetailed, OpsMode } = await load("functions/_lib/opsMode.js");
    const r = await resolveOpsModeDetailed(
      { ui_features: { v11_auto_maintenance: false } },
      { now: jstWeekdayInstant(1) }
    );
    assert.equal(r.ops_mode, OpsMode.PUBLIC);
    assert.equal(r.reason, "default_public");
  });

  it("Flag ON + 月曜 → CLOSED", async () => {
    const { resolveOpsModeDetailed, OpsMode } = await load("functions/_lib/opsMode.js");
    const r = await resolveOpsModeDetailed(
      { ui_features: { v11_auto_maintenance: true } },
      { now: jstWeekdayInstant(1) }
    );
    assert.equal(r.ops_mode, OpsMode.CLOSED);
    assert.equal(r.reason, "research_week_maintenance");
    assert.equal(r.maintenance, true);
  });

  it("Flag ON + 金曜 → CLOSED（土曜 0:00 までメンテ）", async () => {
    const { resolveOpsModeDetailed, OpsMode } = await load("functions/_lib/opsMode.js");
    const r = await resolveOpsModeDetailed(
      { ui_features: { v11_auto_maintenance: true } },
      { now: jstWeekdayInstant(5) }
    );
    assert.equal(r.ops_mode, OpsMode.CLOSED);
    assert.equal(r.reason, "research_week_maintenance");
  });

  it("Flag ON + 土曜 → PUBLIC", async () => {
    const { resolveOpsModeDetailed, OpsMode } = await load("functions/_lib/opsMode.js");
    const r = await resolveOpsModeDetailed(
      { ui_features: { v11_auto_maintenance: true } },
      { now: jstWeekdayInstant(6) }
    );
    assert.equal(r.ops_mode, OpsMode.PUBLIC);
    assert.equal(r.reason, "research_week_open");
    assert.equal(r.maintenance, false);
  });

  it("Flag ON + 日曜 21:00 → CLOSED", async () => {
    const { resolveOpsModeDetailed, OpsMode } = await load("functions/_lib/opsMode.js");
    const r = await resolveOpsModeDetailed(
      { ui_features: { v11_auto_maintenance: true } },
      { now: jstWall(2026, 7, 19, 21, 0) }
    );
    assert.equal(r.ops_mode, OpsMode.CLOSED);
    assert.equal(r.maintenance, true);
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
  });
});

describe("V7 ADMIN vs USER during CLOSED", () => {
  it("USER は予測API拒否 / ADMIN・OPS・DEVELOPER は bypass", async () => {
    const { OpsMode, evaluateOpsAccess } = await load("functions/_lib/opsMode.js");
    const user = evaluateOpsAccess({
      pathname: "/api/predictions",
      opsMode: OpsMode.CLOSED,
      role: "USER",
    });
    assert.equal(user.allow, false);
    assert.equal(user.reason, "ops_closed");

    for (const role of ["ADMIN", "OPS", "DEVELOPER"]) {
      const r = evaluateOpsAccess({
        pathname: "/api/predictions",
        opsMode: OpsMode.CLOSED,
        role,
      });
      assert.equal(r.allow, true, role);
      assert.equal(r.reason, "role_bypass", role);
    }
  });

  it("ADMIN は /api/ops/dashboard 利用可（CLOSED）", async () => {
    const { OpsMode, evaluateOpsAccess } = await load("functions/_lib/opsMode.js");
    const admin = evaluateOpsAccess({
      pathname: "/api/ops/dashboard",
      opsMode: OpsMode.CLOSED,
      role: "ADMIN",
    });
    assert.equal(admin.allow, true);
    assert.equal(admin.reason, "role_bypass");

    const user = evaluateOpsAccess({
      pathname: "/api/ops/dashboard",
      opsMode: OpsMode.CLOSED,
      role: "USER",
    });
    assert.equal(user.allow, false);
  });

  it("login / system/status / public-status は USER でも exempt", async () => {
    const { OpsMode, evaluateOpsAccess, OPS_MODE_EXEMPT_PATHS } = await load(
      "functions/_lib/opsMode.js"
    );
    for (const path of [
      "/api/auth/login",
      "/api/auth/logout",
      "/api/auth/me",
      "/api/system/status",
      "/api/ops/public-status",
      "/api/ops/monitor",
      "/api/admin/invitations",
    ]) {
      assert.equal(OPS_MODE_EXEMPT_PATHS.has(path), true, path);
      const r = evaluateOpsAccess({
        pathname: path,
        opsMode: OpsMode.CLOSED,
        role: "USER",
      });
      assert.equal(r.allow, true, path);
    }
  });

  it("canBypassOpsMode は ADMIN のみ true（USER false）", async () => {
    const { canBypassOpsMode } = await load("functions/_lib/roles.js");
    assert.equal(canBypassOpsMode("ADMIN"), true);
    assert.equal(canBypassOpsMode("USER"), false);
  });
});
