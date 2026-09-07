#!/usr/bin/env node
/**
 * Publish evidence-collector.json for Ops Console (static fallback).
 * Live: GET /api/ops/evidence-collector
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const out = path.join(root, "public/ops-data/evidence-collector.json");

function main() {
  const py = spawnSync(
    "python",
    [
      "-c",
      "import json,sys; sys.path.insert(0,'services/win5-ai'); "
        + "from app.research.monitoring import collect_evidence_monitoring; "
        + "print(json.dumps(collect_evidence_monitoring(), ensure_ascii=False))",
    ],
    { cwd: root, encoding: "utf8" },
  );
  if (py.status !== 0) {
    console.error(py.stderr || py.stdout);
    process.exit(py.status || 1);
  }
  const data = JSON.parse(py.stdout);
  data.schema_version = "expect-v10-evidence-collector/1.0";
  data.published_at = new Date().toISOString();
  fs.writeFileSync(out, JSON.stringify(data, null, 2) + "\n", "utf8");
  console.log("OK", out);
}

main();
