/**
 * PredictionBundle JSON Schema 検証（開発時向け）
 *
 * 環境変数 VALIDATE_CONTRACTS:
 *   unset / "1" / "soft" → 検証し、失敗時は meta.contract_errors を付与（レスポンスは 200）
 *   "strict"             → 検証失敗で 500
 *   "0" / "off"          → 検証スキップ
 *
 * Schema 正本: contracts/single-prediction-bundle/2.0/schema.json
 * BFF 同梱:   functions/_lib/schemas/single-prediction-bundle-2.0.json
 */
import schema from "./schemas/single-prediction-bundle-2.0.js";
import { jsonError } from "./errors.js";

const SCHEMA_VERSION = "single-prediction-bundle/2.0";

function typeOf(v) {
  if (v === null) return "null";
  if (Array.isArray(v)) return "array";
  return typeof v;
}

function matchesType(value, typeSpec) {
  const types = Array.isArray(typeSpec) ? typeSpec : [typeSpec];
  const actual = typeOf(value);
  return types.some((t) => {
    if (t === "integer") return actual === "number" && Number.isInteger(value);
    if (t === "number") return actual === "number" && !Number.isNaN(value);
    return actual === t;
  });
}

function resolveRef(root, ref) {
  if (!ref || !ref.startsWith("#/")) return null;
  const parts = ref.slice(2).split("/");
  let cur = root;
  for (const p of parts) {
    if (!cur || typeof cur !== "object") return null;
    cur = cur[p];
  }
  return cur;
}

function validateAgainst(rootSchema, nodeSchema, value, path, errors) {
  if (!nodeSchema || typeof nodeSchema !== "object") return;

  if (nodeSchema.$ref) {
    const resolved = resolveRef(rootSchema, nodeSchema.$ref);
    if (resolved) validateAgainst(rootSchema, resolved, value, path, errors);
    return;
  }

  if (Object.prototype.hasOwnProperty.call(nodeSchema, "const")) {
    if (value !== nodeSchema.const) {
      errors.push(`${path}: expected const ${JSON.stringify(nodeSchema.const)}`);
    }
  }

  if (nodeSchema.type) {
    if (!matchesType(value, nodeSchema.type)) {
      errors.push(`${path}: expected type ${JSON.stringify(nodeSchema.type)}, got ${typeOf(value)}`);
      return;
    }
  }

  if (typeof value === "string" && typeof nodeSchema.minLength === "number") {
    if (value.length < nodeSchema.minLength) {
      errors.push(`${path}: minLength ${nodeSchema.minLength}`);
    }
  }

  if (typeof value === "number") {
    if (typeof nodeSchema.minimum === "number" && value < nodeSchema.minimum) {
      errors.push(`${path}: minimum ${nodeSchema.minimum}`);
    }
    if (typeof nodeSchema.maximum === "number" && value > nodeSchema.maximum) {
      errors.push(`${path}: maximum ${nodeSchema.maximum}`);
    }
  }

  if (nodeSchema.type === "array" || (Array.isArray(nodeSchema.type) && nodeSchema.type.includes("array"))) {
    if (Array.isArray(value) && nodeSchema.items) {
      value.forEach((item, i) => {
        validateAgainst(rootSchema, nodeSchema.items, item, `${path}[${i}]`, errors);
      });
    }
  }

  if (value && typeof value === "object" && !Array.isArray(value) && nodeSchema.properties) {
    const required = nodeSchema.required || [];
    for (const key of required) {
      if (!Object.prototype.hasOwnProperty.call(value, key)) {
        errors.push(`${path}.${key}: required`);
      }
    }
    for (const [key, propSchema] of Object.entries(nodeSchema.properties)) {
      if (Object.prototype.hasOwnProperty.call(value, key)) {
        validateAgainst(rootSchema, propSchema, value[key], `${path}.${key}`, errors);
      }
    }
  }
}

/**
 * @returns {{ ok: boolean, errors: string[], schema_version: string }}
 */
export function validatePredictionBundle(bundle) {
  const errors = [];
  if (!bundle || typeof bundle !== "object") {
    return { ok: false, errors: ["$: not an object"], schema_version: SCHEMA_VERSION };
  }
  validateAgainst(schema, schema, bundle, "$", errors);
  return { ok: errors.length === 0, errors, schema_version: SCHEMA_VERSION };
}

export function validatePredictionBundleList(items) {
  if (!Array.isArray(items)) {
    return { ok: false, errors: ["$: expected array"], results: [] };
  }
  const results = items.map((b, i) => {
    const r = validatePredictionBundle(b);
    return { index: i, race_id: b && b.race_id, ...r };
  });
  const errors = [];
  results.forEach((r) => {
    r.errors.forEach((e) => errors.push(`[${r.index} ${r.race_id || "?"}] ${e}`));
  });
  return { ok: errors.length === 0, errors, results };
}

export function contractValidationMode(context) {
  const raw = String((context.env && context.env.VALIDATE_CONTRACTS) || "soft").toLowerCase();
  if (raw === "0" || raw === "off" || raw === "false") return "off";
  if (raw === "strict") return "strict";
  return "soft";
}

/**
 * 検証結果を meta に載せ、strict 時は Response を返す。
 * @returns {{ data, meta, errorResponse?: Response }}
 */
export function applyBundleValidation(context, data, meta = {}) {
  const mode = contractValidationMode(context);
  if (mode === "off") {
    return { data, meta: { ...meta, contract: "PredictionBundle", schema_version: SCHEMA_VERSION } };
  }

  const isList = Array.isArray(data);
  const result = isList ? validatePredictionBundleList(data) : validatePredictionBundle(data);
  const nextMeta = {
    ...meta,
    contract: "PredictionBundle",
    schema_version: SCHEMA_VERSION,
    contract_validated: true,
    contract_ok: result.ok,
  };

  if (!result.ok) {
    nextMeta.contract_errors = result.errors.slice(0, 40);
    console.warn(
      "[PredictionBundle contract]",
      result.errors.slice(0, 8).join(" | ")
    );
    if (mode === "strict") {
      return {
        data,
        meta: nextMeta,
        errorResponse: jsonError("CONTRACT_INVALID", "PredictionBundle failed schema validation", 500, {
          schema_version: SCHEMA_VERSION,
          errors: result.errors.slice(0, 40),
        }),
      };
    }
  }

  return { data, meta: nextMeta };
}
