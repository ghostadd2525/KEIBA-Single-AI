/**
 * JSON Schema サブセット検証（Node / テスト / CI 共用）
 * Draft 2020-12 の required / type / const / $ref / min|max / minLength を扱う
 */

export function typeOf(v) {
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

export function validateAgainst(rootSchema, nodeSchema, value, path, errors) {
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
      errors.push(
        `${path}: expected type ${JSON.stringify(nodeSchema.type)}, got ${typeOf(value)}`
      );
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

  if (
    nodeSchema.type === "array" ||
    (Array.isArray(nodeSchema.type) && nodeSchema.type.includes("array"))
  ) {
    if (Array.isArray(value) && nodeSchema.items) {
      value.forEach((item, i) => {
        validateAgainst(rootSchema, nodeSchema.items, item, `${path}[${i}]`, errors);
      });
    }
  }

  if (value && typeof value === "object" && !Array.isArray(value) && nodeSchema.properties) {
    for (const key of nodeSchema.required || []) {
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

export function validateWithSchema(schema, data) {
  const errors = [];
  if (data === undefined) {
    return { ok: false, errors: ["$: undefined"] };
  }
  validateAgainst(schema, schema, data, "$", errors);
  return { ok: errors.length === 0, errors };
}

/** $defs 内の定義名で検証（Auth など複合 schema 用） */
export function validateDef(schema, defName, data) {
  const errors = [];
  if (data === undefined) {
    return { ok: false, errors: ["$: undefined"] };
  }
  validateAgainst(schema, { $ref: `#/$defs/${defName}` }, data, "$", errors);
  return { ok: errors.length === 0, errors };
}
