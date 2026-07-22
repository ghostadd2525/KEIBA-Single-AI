/**
 * Auto-maintenance weekday verification report helper (API + login).
 * Run against local wrangler with v11_auto_maintenance=true.
 */
import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const BASE = process.env.CANARY_BASE || "http://127.0.0.1:8788";
const OUT = join(dirname(fileURLToPath(import.meta.url)), "../../docs/ops/canary-v1.1-evidence/auto-maint-verify");
mkdirSync(OUT, { recursive: true });

const results = [];

async function req(path, { method = "GET", token, body } = {}) {
  const headers = { Accept: "application/json" };
  if (token) headers.Authorization = "Bearer " + token;
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json = null;
  try {
    json = JSON.parse(text);
  } catch {
    /* ignore */
  }
  return { status: res.status, url: BASE + path, json, text: text.slice(0, 300) };
}

async function login(id, password) {
  const r = await req("/api/auth/login", {
    method: "POST",
    body: { id, password },
  });
  const token = r.json && r.json.data && r.json.data.access_token;
  return { ...r, token };
}

function record(name, pass, detail) {
  results.push({ name, pass: !!pass, ...detail });
  console.log((pass ? "PASS" : "FAIL") + "  " + name + "  " + JSON.stringify(detail));
}

async function main() {
  const status0 = await req("/api/ops/public-status");
  record("public-status weekday closed", status0.status === 200 && status0.json?.data?.ops_mode === "CLOSED", {
    http: status0.status,
    data: status0.json?.data,
  });

  // ADMIN
  const adminLogin = await login("admin-canary", "CanaryAdmin1!");
  record("ADMIN login", adminLogin.status === 200 && !!adminLogin.token, {
    http: adminLogin.status,
    url: "/api/auth/login",
  });
  const adminPred = await req("/api/predictions", { token: adminLogin.token });
  record("ADMIN predictions", adminPred.status === 200, { http: adminPred.status, url: "/api/predictions" });
  const adminChat = await req("/api/conversation/chat", {
    method: "POST",
    token: adminLogin.token,
    body: { message: "hello canary", ui: "chat" },
  });
  record("ADMIN conversation", adminChat.status === 200 || adminChat.status === 502 || adminChat.status === 503 === false, {
    http: adminChat.status,
    note: "ADMIN must not be OPS_CLOSED; 200/4xx/502 ok if AI down, not OPS_CLOSED",
    code: adminChat.json?.error?.code,
  });
  // Fix: ADMIN conversation should NOT be OPS_CLOSED
  const adminChatOk = adminChat.status !== 503 || adminChat.json?.error?.code !== "OPS_CLOSED";
  results[results.length - 1].pass = adminChatOk;

  // USER
  const userLogin = await login("user-canary", "CanaryUser1!");
  record("USER login", userLogin.status === 200 && !!userLogin.token, {
    http: userLogin.status,
    url: "/api/auth/login",
  });
  const userPred = await req("/api/predictions", { token: userLogin.token });
  record("USER predictions OPS_CLOSED", userPred.status === 503 && userPred.json?.error?.code === "OPS_CLOSED", {
    http: userPred.status,
    code: userPred.json?.error?.code,
    url: "/api/predictions",
  });
  const userChat = await req("/api/conversation/chat", {
    method: "POST",
    token: userLogin.token,
    body: { message: "hello", ui: "chat" },
  });
  record("USER conversation OPS_CLOSED", userChat.status === 503 && userChat.json?.error?.code === "OPS_CLOSED", {
    http: userChat.status,
    code: userChat.json?.error?.code,
    url: "/api/conversation/chat",
  });

  // Invite start (一時ID) — auth exempt; after setup would be USER
  const invite = await req("/api/auth/invite/start", {
    method: "POST",
    body: { invite_id: "BETA-F6D1-E07E" },
  });
  record("一時ID invite/start", invite.status === 200 || invite.status === 409 || invite.status === 400, {
    http: invite.status,
    note: "invite endpoint available during CLOSED",
    body: invite.json?.error || invite.json?.data || invite.json,
  });

  writeFileSync(join(OUT, "api-results.json"), JSON.stringify({ base: BASE, at: new Date().toISOString(), results }, null, 2));
  const failed = results.filter((r) => !r.pass);
  console.log("\nSummary", results.length - failed.length, "/", results.length);
  if (failed.length) process.exit(1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
