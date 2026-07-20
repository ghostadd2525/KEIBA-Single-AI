/**
 * Build Evidence Index from scanned events (I-1 + I-2 extensions).
 *
 * Outputs (Development only — never writes Production):
 *   development/index/latest.json
 *   development/index/by-date/{YYYY-MM-DD}.json
 *   development/index/by-event-type/{event_type}.json
 *   development/index/by-event-type/summary.json
 *   development/index/by-model-version/{model_version|unknown}.json  (extensible)
 *   development/index/clusters/{cluster_id}.json
 */
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { createHash } from "node:crypto";

function clusterId(ev) {
  if (ev.fingerprint) {
    const hex = ev.fingerprint.replace(/^sha256:/, "").slice(0, 12);
    return `fp-${ev.event_type}-${hex}`;
  }
  const raw = `${ev.event_type}|${ev.race_id || ev.race_date}`;
  const h = createHash("sha256").update(raw).digest("hex").slice(0, 12);
  return `fp-${ev.event_type}-${h}`;
}

function toEventRef(e) {
  return {
    event_id: e.event_id,
    event_type: e.event_type,
    race_date: e.race_date,
    race_id: e.race_id,
    fingerprint: e.fingerprint ?? null,
    path: e.path,
    model_version: e.model_version ?? null,
  };
}

function sanitizeModelVersionKey(mv) {
  if (mv == null || String(mv).trim() === "") return "unknown";
  return String(mv)
    .trim()
    .replace(/[^\w.\-]+/g, "_")
    .slice(0, 120);
}

/**
 * @param {object} scanResult from scanEvidence
 * @param {string} devRoot development/
 * @param {string | null} dateFilter
 */
export function buildIndex(scanResult, devRoot, dateFilter) {
  /** @type {Map<string, object>} */
  const clusters = new Map();
  /** @type {Record<string, number>} */
  const countsByModelVersion = {};

  for (const ev of scanResult.events) {
    const id = clusterId(ev);
    if (!clusters.has(id)) {
      clusters.set(id, {
        cluster_id: id,
        fingerprint: ev.fingerprint,
        event_type: ev.event_type,
        count: 0,
        event_ids: [],
        sample_path: ev.path,
        race_dates: new Set(),
        model_versions: new Set(),
      });
    }
    const c = clusters.get(id);
    c.count += 1;
    if (!c.event_ids.includes(ev.event_id)) c.event_ids.push(ev.event_id);
    c.race_dates.add(ev.race_date);
    c.model_versions.add(ev.model_version || "unknown");

    const mvKey = ev.model_version || "unknown";
    countsByModelVersion[mvKey] = (countsByModelVersion[mvKey] || 0) + 1;
  }

  const clusterList = [...clusters.values()]
    .map((c) => ({
      cluster_id: c.cluster_id,
      fingerprint: c.fingerprint,
      event_type: c.event_type,
      count: c.count,
      event_ids: c.event_ids,
      sample_path: c.sample_path,
      race_dates: [...c.race_dates].sort(),
      model_versions: [...c.model_versions].sort(),
    }))
    .sort((a, b) => b.count - a.count);

  const index = {
    schema_version: "expect-evidence-index/1.0",
    generated_at: new Date().toISOString(),
    source_root: "evidence/improvement",
    filter_date: dateFilter,
    corpus_status: scanResult.total > 0 ? "populated" : "empty",
    counts_by_event_type: scanResult.countsByType,
    counts_by_model_version: countsByModelVersion,
    event_total: scanResult.total,
    dates: scanResult.dates,
    events: scanResult.events.map(toEventRef),
    clusters: clusterList,
    dimensions: {
      by_date: true,
      by_event_type: true,
      by_model_version: true,
      clusters: true,
    },
  };

  const outDir = join(devRoot, "index");
  mkdirSync(outDir, { recursive: true });
  mkdirSync(join(outDir, "by-date"), { recursive: true });
  mkdirSync(join(outDir, "by-event-type"), { recursive: true });
  mkdirSync(join(outDir, "by-model-version"), { recursive: true });
  mkdirSync(join(outDir, "clusters"), { recursive: true });

  writeFileSync(join(outDir, "latest.json"), JSON.stringify(index, null, 2) + "\n", "utf8");
  writeFileSync(
    join(outDir, "by-event-type", "summary.json"),
    JSON.stringify(index, null, 2) + "\n",
    "utf8"
  );

  for (const d of scanResult.dates) {
    const dayEvents = scanResult.events.filter((e) => e.race_date === d);
    const dayClusters = clusterList
      .map((c) => {
        const ids = new Set(
          dayEvents.filter((e) => clusterId(e) === c.cluster_id).map((e) => e.event_id)
        );
        if (ids.size === 0) return null;
        return {
          ...c,
          count: ids.size,
          event_ids: c.event_ids.filter((id) => ids.has(id)),
          race_dates: [d],
        };
      })
      .filter(Boolean);

    const dayCounts = {};
    const dayMv = {};
    for (const e of dayEvents) {
      dayCounts[e.event_type] = (dayCounts[e.event_type] || 0) + 1;
      const mk = e.model_version || "unknown";
      dayMv[mk] = (dayMv[mk] || 0) + 1;
    }

    const dayIndex = {
      schema_version: "expect-evidence-index/1.0",
      generated_at: index.generated_at,
      source_root: "evidence/improvement",
      filter_date: d,
      corpus_status: dayEvents.length > 0 ? "populated" : "empty",
      counts_by_event_type: dayCounts,
      counts_by_model_version: dayMv,
      event_total: dayEvents.length,
      dates: [d],
      events: dayEvents.map(toEventRef),
      clusters: dayClusters,
      dimensions: index.dimensions,
    };
    writeFileSync(
      join(outDir, "by-date", `${d}.json`),
      JSON.stringify(dayIndex, null, 2) + "\n",
      "utf8"
    );
  }

  const types = new Set(scanResult.events.map((e) => e.event_type));
  for (const eventType of types) {
    const typeEvents = scanResult.events.filter((e) => e.event_type === eventType);
    const typeClusters = clusterList.filter((c) => c.event_type === eventType);
    const typeMv = {};
    for (const e of typeEvents) {
      const mk = e.model_version || "unknown";
      typeMv[mk] = (typeMv[mk] || 0) + 1;
    }
    const typeIndex = {
      schema_version: "expect-evidence-index/1.0",
      generated_at: index.generated_at,
      source_root: "evidence/improvement",
      filter_date: dateFilter,
      corpus_status: typeEvents.length > 0 ? "populated" : "empty",
      counts_by_event_type: { [eventType]: typeEvents.length },
      counts_by_model_version: typeMv,
      event_total: typeEvents.length,
      dates: [...new Set(typeEvents.map((e) => e.race_date))].sort(),
      events: typeEvents.map(toEventRef),
      clusters: typeClusters,
      dimensions: index.dimensions,
    };
    writeFileSync(
      join(outDir, "by-event-type", `${eventType}.json`),
      JSON.stringify(typeIndex, null, 2) + "\n",
      "utf8"
    );
  }

  // by-model-version — always create dir; write slices when versions present
  const modelVersions = new Set(
    scanResult.events.map((e) => e.model_version || "unknown")
  );
  if (modelVersions.size === 0) {
    writeFileSync(
      join(outDir, "by-model-version", "README.md"),
      "# by-model-version\n\nReserved dimension. Populated when Evidence carries `model_version`.\n",
      "utf8"
    );
  }
  for (const mv of modelVersions) {
    const mvEvents = scanResult.events.filter(
      (e) => (e.model_version || "unknown") === mv
    );
    const key = sanitizeModelVersionKey(mv);
    const mvCounts = {};
    for (const e of mvEvents) {
      mvCounts[e.event_type] = (mvCounts[e.event_type] || 0) + 1;
    }
    const mvIndex = {
      schema_version: "expect-evidence-index/1.0",
      generated_at: index.generated_at,
      source_root: "evidence/improvement",
      filter_date: dateFilter,
      filter_model_version: mv,
      corpus_status: mvEvents.length > 0 ? "populated" : "empty",
      counts_by_event_type: mvCounts,
      counts_by_model_version: { [mv]: mvEvents.length },
      event_total: mvEvents.length,
      dates: [...new Set(mvEvents.map((e) => e.race_date))].sort(),
      events: mvEvents.map(toEventRef),
      clusters: clusterList.filter((c) =>
        (c.model_versions || []).includes(mv)
      ),
      dimensions: index.dimensions,
    };
    writeFileSync(
      join(outDir, "by-model-version", `${key}.json`),
      JSON.stringify(mvIndex, null, 2) + "\n",
      "utf8"
    );
  }

  for (const c of clusterList) {
    const clusterEvents = scanResult.events
      .filter((e) => clusterId(e) === c.cluster_id)
      .map(toEventRef);
    const clusterDoc = {
      schema_version: "expect-evidence-index/1.0",
      generated_at: index.generated_at,
      source_root: "evidence/improvement",
      cluster: c,
      events: clusterEvents,
    };
    writeFileSync(
      join(outDir, "clusters", `${c.cluster_id}.json`),
      JSON.stringify(clusterDoc, null, 2) + "\n",
      "utf8"
    );
  }

  return index;
}

export { clusterId, toEventRef, sanitizeModelVersionKey };
