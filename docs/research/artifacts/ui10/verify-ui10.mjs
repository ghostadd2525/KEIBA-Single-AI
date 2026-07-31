import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { composeExplainUx } from "../../../../functions/_lib/explainUxComposer.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../../../..");
const ART = join(ROOT, "docs/research/artifacts/ui10");
const SRC = join(
  "C:/Users/Mr.me/expect-keiba-ai/docs/research/artifacts/ui9"
);

mkdirSync(ART, { recursive: true });

const ids = [
  "2026-07-26-01-01",
  "2026-07-26-01-07",
  "2026-07-26-01-11",
];

function loadBundle(id) {
  const j = JSON.parse(readFileSync(join(SRC, `${id}.json`), "utf8"));
  return j.data;
}

const rows = ids.map((id) => {
  const b = loadBundle(id);
  const ux = composeExplainUx(b);
  const texts = ux.blocks.map((bl) => ({
    title: bl.title,
    paragraphs: bl.paragraphs,
    bullets: bl.bullets,
  }));
  return {
    race_id: id,
    honmei: ux.signals.honmei,
    fingerprint: ux.fingerprint,
    blocks: texts,
    flat: ux.blocks
      .flatMap((bl) => [...(bl.paragraphs || []), ...(bl.bullets || [])])
      .join("\n"),
  };
});

const fps = new Set(rows.map((r) => r.fingerprint));
assert.equal(fps.size, rows.length, "fingerprints must differ per race");

// 旧テンプレ句が主文に残っていないこと
const banned = "を◎にしたのは、AI予測では1番手で、2番手との差も相対的に大きいため";
for (const r of rows) {
  assert.equal(r.flat.includes(banned), false, `banned template in ${r.race_id}`);
}

// ブロック間で同一全文が連続しない（fingerprint 前の dedupe 後）
for (const r of rows) {
  const paras = r.blocks.flatMap((b) => b.paragraphs);
  for (let i = 1; i < paras.length; i++) {
    assert.notEqual(paras[i], paras[i - 1], `consecutive dup in ${r.race_id}`);
  }
}

writeFileSync(join(ART, "compare.json"), JSON.stringify(rows, null, 2), "utf8");
console.log("UI10 verify PASS", {
  n: rows.length,
  fingerprints: rows.map((r) => r.fingerprint),
});
