/**
 * V1.1 Canary harness — Auto Maintenance priority + Flag OFF baseline (Node)
 * Does not mutate committed beta.json.
 */
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");

async function load(rel) {
  return import(pathToFileURL(join(ROOT, rel)).href);
}

function jstWeekdayInstant(weekday) {
  const baseSun = Date.UTC(2026, 6, 19, 3, 0, 0);
  return new Date(baseSun + weekday * 86400000);
}

const results = [];

function ok(name, pass, detail) {
  results.push({ name, pass: !!pass, detail: detail || "" });
  console.log((pass ? "PASS" : "FAIL") + "  " + name + (detail ? " — " + detail : ""));
}

async function main() {
  const { resolveOpsModeDetailed, OpsMode, evaluateOpsAccess } = await load(
    "functions/_lib/opsMode.js"
  );

  // Flag OFF baseline
  {
    const r = await resolveOpsModeDetailed(
      { ui_features: { v11_auto_maintenance: false }, maintenance_mode: false },
      { now: jstWeekdayInstant(1) }
    );
    ok("Flag OFF weekday = PUBLIC", r.ops_mode === OpsMode.PUBLIC, r.reason);
  }

  // Flag ON weekday/weekend
  {
    const mon = await resolveOpsModeDetailed(
      { ui_features: { v11_auto_maintenance: true } },
      { now: jstWeekdayInstant(1) }
    );
    ok("Flag ON Mon = CLOSED", mon.ops_mode === OpsMode.CLOSED && mon.reason === "research_week_maintenance");
    const sat = await resolveOpsModeDetailed(
      { ui_features: { v11_auto_maintenance: true } },
      { now: jstWeekdayInstant(6) }
    );
    ok("Flag ON Sat = PUBLIC", sat.ops_mode === OpsMode.PUBLIC && sat.reason === "research_week_open");
    const fri = await resolveOpsModeDetailed(
      { ui_features: { v11_auto_maintenance: true } },
      { now: jstWeekdayInstant(5) }
    );
    ok("Flag ON Fri = CLOSED (until Sat 00:00)", fri.ops_mode === OpsMode.CLOSED);
  }

  // Manual priority
  {
    const forcePublic = await resolveOpsModeDetailed(
      {
        ops_mode: "PUBLIC",
        ui_features: { v11_auto_maintenance: true },
      },
      { now: jstWeekdayInstant(1) }
    );
    ok("ops_mode PUBLIC beats auto", forcePublic.ops_mode === OpsMode.PUBLIC && forcePublic.manual_override);

    const forceClosed = await resolveOpsModeDetailed(
      {
        maintenance_mode: true,
        ui_features: { v11_auto_maintenance: true },
      },
      { now: jstWeekdayInstant(6) }
    );
    ok("maintenance_mode beats weekend", forceClosed.ops_mode === OpsMode.CLOSED);

    const opsClosed = await resolveOpsModeDetailed(
      {
        ops_mode: "CLOSED",
        maintenance_mode: false,
        ui_features: { v11_auto_maintenance: true },
      },
      { now: jstWeekdayInstant(6) }
    );
    ok("ops_mode CLOSED beats weekend", opsClosed.ops_mode === OpsMode.CLOSED);
  }

  // Rollback = Flag OFF
  {
    const r = await resolveOpsModeDetailed(
      {
        ui_features: { v11_auto_maintenance: false },
        ops_mode: null,
        maintenance_mode: false,
      },
      { now: jstWeekdayInstant(1) }
    );
    ok("Rollback Flag OFF = PUBLIC on weekday", r.ops_mode === OpsMode.PUBLIC);
  }

  // ADMIN bypass vs USER
  {
    const user = evaluateOpsAccess({
      pathname: "/api/predictions",
      opsMode: OpsMode.CLOSED,
      role: "USER",
    });
    const admin = evaluateOpsAccess({
      pathname: "/api/predictions",
      opsMode: OpsMode.CLOSED,
      role: "ADMIN",
    });
    ok("USER blocked when CLOSED", user.allow === false);
    ok("ADMIN bypass when CLOSED", admin.allow === true);
  }

  // Flag defaults in beta.json (V7 Maintenance Mode: auto-maint ON)
  {
    const fs = await import("node:fs");
    const cfg = JSON.parse(fs.readFileSync(join(ROOT, "config/beta.json"), "utf8"));
    const pub = JSON.parse(fs.readFileSync(join(ROOT, "public/config/beta.json"), "utf8"));
    ok(
      "Committed v11_auto_maintenance ON (V7 Research Week)",
      cfg.ui_features.v11_auto_maintenance === true &&
        pub.ui_features.v11_auto_maintenance === true
    );
    const uiFlagsOff = [
      "v11_mobile",
      "v11_home",
      "v11_races",
      "v11_race_detail",
      "v11_explain",
      "v11_confidence",
      "v11_collector_status",
      "v11_system_health",
    ];
    const experimentalOff = uiFlagsOff.every((k) => cfg.ui_features[k] === false);
    ok(
      "Canary UI flags default false (except loading/ops/auto-maint)",
      experimentalOff &&
        cfg.ui_features.v11_loading_errors === true &&
        cfg.ui_features.v11_ops_dashboard === true &&
        cfg.ui_features.v11_auto_maintenance === true
    );
  }

  const failed = results.filter((r) => !r.pass);
  console.log("\nSummary:", results.length - failed.length, "/", results.length, "PASS");
  if (failed.length) process.exit(1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
