#!/usr/bin/env node
/**
 * Scan evidence/improvement for event JSON files.
 */
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

export const EVENT_TYPES = [
  "miss",
  "feature_missing",
  "prediction_failed",
  "result_sync_failed",
];

/**
 * @param {string} root evidence/improvement
 * @param {string | null} dateFilter YYYY-MM-DD or null for all
 */
export function scanEvidence(root, dateFilter = null) {
  /** @type {Array<object>} */
  const events = [];
  const countsByType = Object.fromEntries(EVENT_TYPES.map((t) => [t, 0]));
  const dates = new Set();

  if (!existsSync(root)) {
    return { events, countsByType, dates: [], total: 0 };
  }

  for (const eventType of EVENT_TYPES) {
    const typeDir = join(root, eventType);
    if (!existsSync(typeDir)) continue;

    for (const dateName of readdirSync(typeDir)) {
      if (dateFilter && dateName !== dateFilter) continue;
      const dateDir = join(typeDir, dateName);
      if (!statSync(dateDir).isDirectory()) continue;
      dates.add(dateName);

      for (const file of readdirSync(dateDir)) {
        if (!file.endsWith(".json")) continue;
        const full = join(dateDir, file);
        if (!statSync(full).isFile()) continue;
        try {
          const doc = JSON.parse(readFileSync(full, "utf8"));
          if (!doc || typeof doc !== "object") continue;
          const rel = `evidence/improvement/${eventType}/${dateName}/${file}`;
          events.push({
            event_type: doc.event_type || eventType,
            event_id: doc.event_id || `${eventType}:${file}`,
            race_date: doc.race_date || dateName,
            race_id: doc.race_id ?? null,
            fingerprint: doc.fingerprint || null,
            path: rel,
            payload: doc.payload || {},
            model_version:
              (doc.version && doc.version.model_version) ||
              (doc.payload && doc.payload.model_version) ||
              null,
          });
          countsByType[eventType] = (countsByType[eventType] || 0) + 1;
        } catch {
          /* skip invalid json */
        }
      }
    }
  }

  // unknown future types under improvement/
  for (const name of readdirSync(root)) {
    if (EVENT_TYPES.includes(name) || name === "manifest" || name === "README.md") continue;
    const unknownDir = join(root, name);
    if (!statSync(unknownDir).isDirectory()) continue;
    for (const dateName of readdirSync(unknownDir)) {
      if (dateFilter && dateName !== dateFilter) continue;
      const dateDir = join(unknownDir, dateName);
      if (!statSync(dateDir).isDirectory()) continue;
      dates.add(dateName);
      for (const file of readdirSync(dateDir)) {
        if (!file.endsWith(".json")) continue;
        const full = join(dateDir, file);
        try {
          const doc = JSON.parse(readFileSync(full, "utf8"));
          const rel = `evidence/improvement/${name}/${dateName}/${file}`;
          events.push({
            event_type: doc.event_type || name,
            event_id: doc.event_id || `${name}:${file}`,
            race_date: doc.race_date || dateName,
            race_id: doc.race_id ?? null,
            fingerprint: doc.fingerprint || null,
            path: rel,
            payload: doc.payload || {},
            model_version:
              (doc.version && doc.version.model_version) ||
              (doc.payload && doc.payload.model_version) ||
              null,
          });
          countsByType[name] = (countsByType[name] || 0) + 1;
        } catch {
          /* skip */
        }
      }
    }
  }

  return {
    events,
    countsByType,
    dates: [...dates].sort(),
    total: events.length,
  };
}
