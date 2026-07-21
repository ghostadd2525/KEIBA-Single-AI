/**
 * Phase9-A: Python が loopback 以外で listen していないかの簡易チェック（ローカル用）
 * 使い方: node scripts/check-ai-bind.mjs
 */
import net from "node:net";

const host = process.env.AI_HOST || "127.0.0.1";
const port = Number(process.env.AI_PORT || 8000);

function probe(targetHost) {
  return new Promise((resolve) => {
    const socket = net.connect({ host: targetHost, port, timeout: 800 }, () => {
      socket.end();
      resolve({ host: targetHost, ok: true });
    });
    socket.on("error", () => resolve({ host: targetHost, ok: false }));
    socket.on("timeout", () => {
      socket.destroy();
      resolve({ host: targetHost, ok: false });
    });
  });
}

const results = {
  configured: { host, port },
  loopback: await probe("127.0.0.1"),
  allInterfaces: await probe("0.0.0.0"),
};

console.log(JSON.stringify(results, null, 2));

if (host !== "127.0.0.1" && host !== "localhost") {
  console.error("WARN: AI_HOST should be 127.0.0.1 behind cloudflared");
  process.exitCode = 2;
}
