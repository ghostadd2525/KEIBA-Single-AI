/**
 * Phase10 — β運営設定（ASSETS: /config/beta.json）
 */
import { loadAssetJson } from "./aiProxy.js";

const DEFAULTS = {
  schema_version: "expect-beta-config/1.0",
  beta_name: "Expect KEIBA AI — Invitation Beta",
  maintenance_mode: false,
  maintenance_message: "ただいまメンテナンス中です。しばらくしてから再度お試しください。",
  /** OPS-1: PUBLIC | CLOSED（未設定時は maintenance_mode から導出） */
  ops_mode: null,
  /** OPS-1A: 管理者 user_id 一覧（users.json の role と併用） */
  admin_user_ids: [],
  terms_version: "2026-07-19",
  invitation_required: true,
  max_concurrent_sessions: null,
  audit: { enabled: true, sink: "jsonl" },
  /** Version 1.1 UI Feature Flags（未知キー無視・後方互換） */
  ui_features: {
    v11_loading_errors: true,
    v11_mobile: false,
    v11_home: false,
    v11_races: false,
    v11_race_detail: false,
    v11_explain: false,
    v11_confidence: false,
    v11_collector_status: false,
    v11_system_health: false,
    v11_ops_dashboard: false,
  },
};

let cache = null;

export async function getBetaConfig(context) {
  if (cache) return cache;
  const doc = await loadAssetJson(context, "/config/beta.json");
  cache = {
    ...DEFAULTS,
    ...(doc && typeof doc === "object" ? doc : {}),
    audit: {
      ...DEFAULTS.audit,
      ...(doc && doc.audit && typeof doc.audit === "object" ? doc.audit : {}),
    },
    ui_features: {
      ...DEFAULTS.ui_features,
      ...(doc && doc.ui_features && typeof doc.ui_features === "object"
        ? doc.ui_features
        : {}),
    },
  };
  return cache;
}

export function _resetBetaConfigCacheForTests() {
  cache = null;
}

export function _setBetaConfigForTests(cfg) {
  cache = { ...DEFAULTS, ...cfg, audit: { ...DEFAULTS.audit, ...(cfg.audit || {}) } };
}
