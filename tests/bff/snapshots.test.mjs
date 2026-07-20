import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadSchemas, readJson } from "../helpers/load.mjs";
import {
  analysisGetEnvelope,
  authLoginEnvelope,
  authLogoutEnvelope,
  authMeEnvelope,
  kaobaChatEnvelope,
  predictionGetEnvelope,
  predictionListEnvelope,
  stableStringify,
} from "./build-envelope.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SNAP_DIR = join(__dirname, "__snapshots__");
const UPDATE = process.env.UPDATE_SNAPSHOTS === "1";

function assertSnapshot(name, actualObj) {
  mkdirSync(SNAP_DIR, { recursive: true });
  const path = join(SNAP_DIR, name);
  const actual = stableStringify(actualObj);
  if (UPDATE || !existsSync(path)) {
    writeFileSync(path, actual, "utf8");
  }
  const expected = readFileSync(path, "utf8");
  assert.equal(actual, expected, `snapshot mismatch: ${name} (UPDATE_SNAPSHOTS=1 で更新可)`);
}

describe("BFF response snapshots", () => {
  const schemas = loadSchemas();
  const bundle = readJson("fixtures/prediction-bundle/valid-hanshin-11.json");
  const analysis = readJson("fixtures/analysis/valid-hanshin-11.json");
  const login = readJson("fixtures/auth/login-response.json");
  const me = readJson("fixtures/auth/me-response.json");
  const logout = readJson("fixtures/auth/logout-response.json");
  const kaoba = readJson("fixtures/kaoba/chat-response.json");
  const kaobaNoRace = readJson("fixtures/kaoba/chat-response-no-race.json");

  it("GET /api/predictions/:id エンベロープ", () => {
    assertSnapshot("predictions-id.envelope.json", predictionGetEnvelope(bundle, schemas));
  });

  it("GET /api/predictions エンベロープ（1件リスト）", () => {
    assertSnapshot("predictions-list.envelope.json", predictionListEnvelope([bundle], schemas));
  });

  it("GET /api/analysis/:id エンベロープ", () => {
    assertSnapshot("analysis-id.envelope.json", analysisGetEnvelope(analysis, schemas));
  });

  it("POST /api/auth/login エンベロープ", () => {
    assertSnapshot("auth-login.envelope.json", authLoginEnvelope(login, schemas));
  });

  it("GET /api/auth/me エンベロープ", () => {
    assertSnapshot("auth-me.envelope.json", authMeEnvelope(me, schemas));
  });

  it("POST /api/auth/logout エンベロープ", () => {
    assertSnapshot("auth-logout.envelope.json", authLogoutEnvelope(logout, schemas));
  });

  it("POST /api/kaoba/chat エンベロープ（race 参照）", () => {
    assertSnapshot(
      "kaoba-chat.envelope.json",
      kaobaChatEnvelope(kaoba, schemas, "20260719_hanshin_11")
    );
  });

  it("POST /api/kaoba/chat エンベロープ（race なし）", () => {
    assertSnapshot("kaoba-chat-no-race.envelope.json", kaobaChatEnvelope(kaobaNoRace, schemas, null));
  });
});
