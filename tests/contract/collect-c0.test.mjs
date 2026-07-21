import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { ROOT } from "../helpers/load.mjs";
import { validateWithSchema } from "../../contracts/lib/schema-validate.mjs";

const SCHEMA_PATH = join(
  ROOT,
  "contracts",
  "expect-collect-week-manifest",
  "1.1",
  "schema.json"
);

function sampleManifest(overrides = {}) {
  return {
    schema_version: "expect-collect-week-manifest/1.1",
    week_id: "2026-07-25",
    calendar_version: "jra-calendar-2026-w30",
    planner_run_id: "planner-2026-07-25-test",
    generated_at: "2026-07-21T06:00:00+09:00",
    races: {
      total_races_expected: 72,
      total_races_ready: 68,
      venue_count: 3,
      race_count_per_venue: {
        "2026-07-25": { 函館: 12, 小倉: 12, 新潟: 12 },
        "2026-07-26": { 函館: 12, 小倉: 12, 新潟: 12 },
      },
      prediction_ready_races: 65,
    },
    collect: { ready: 180, partial: 12, failed: 2, retry: 14 },
    budget: { daily_limit: 150, used: 142, remaining: 8 },
    status: {
      prediction_ready: false,
      complete_ready: false,
      dynamic_ready: false,
      dynamic_stale: false,
    },
    ...overrides,
  };
}

describe("collect-c0 manifest contract", () => {
  const schema = JSON.parse(readFileSync(SCHEMA_PATH, "utf8"));

  it("schema file defines required C-0 fields", () => {
    assert.equal(schema.properties.schema_version.const, "expect-collect-week-manifest/1.1");
    for (const key of [
      "week_id",
      "calendar_version",
      "planner_run_id",
      "generated_at",
      "races",
      "collect",
      "budget",
      "status",
    ]) {
      assert.ok(schema.required.includes(key), `required ${key}`);
    }
  });

  it("valid sample manifest passes schema", () => {
    const result = validateWithSchema(schema, sampleManifest());
    assert.equal(result.ok, true, result.errors?.join("; "));
  });

  it("missing calendar_version fails", () => {
    const m = sampleManifest();
    delete m.calendar_version;
    const result = validateWithSchema(schema, m);
    assert.equal(result.ok, false);
    assert.ok(result.errors.some((e) => e.includes("calendar_version")));
  });

  it("missing races.total_races_expected fails", () => {
    const m = sampleManifest();
    delete m.races.total_races_expected;
    const result = validateWithSchema(schema, m);
    assert.equal(result.ok, false);
  });

  it("collect block uses ready/partial/failed/retry", () => {
    const m = sampleManifest();
    assert.ok("ready" in m.collect);
    assert.ok("retry" in m.collect);
    assert.equal(typeof m.status.prediction_ready, "boolean");
  });
});

describe("collect-c0 design alignment notes", () => {
  it("manifest uses status not gates (C-0 contract)", () => {
    const m = sampleManifest();
    assert.ok(m.status);
    assert.equal(m.status.prediction_ready, false);
    assert.equal("gates" in m, false);
  });

  it("manifest uses collect not jobs (C-0 contract)", () => {
    const m = sampleManifest();
    assert.ok(m.collect);
    assert.equal("jobs" in m, false);
  });
});
