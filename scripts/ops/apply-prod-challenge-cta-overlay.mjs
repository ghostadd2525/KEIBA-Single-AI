#!/usr/bin/env node
/**
 * Dirty-safe Challenge CTA overlay.
 *
 * Applies ONLY:
 *   - catalog-identity.js  ← PR #8 / 4fba49a content
 *   - race.html CTA bind   ← ExpectUiTestRace.showChallengeCtaForRace
 *                            → ExpectCatalogIdentity + applyChallengeCta
 *   - catalog-identity.js?v=2 → ?v=3
 *
 * Does not copy git public/ over Production.
 * Does not deploy. Does not change other ?v= references.
 *
 * Usage:
 *   node scripts/ops/apply-prod-challenge-cta-overlay.mjs \
 *     --prod-public /path/to/production/public
 *
 * Then Owner deploys THAT directory (not git public/).
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "../..");

function parseArgs(argv) {
  const out = { prodPublic: "" };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--prod-public") out.prodPublic = argv[++i] || "";
  }
  return out;
}

const OLD_BIND = `    var challengeLink = document.getElementById("challengePurchaseLink");
    var challengeIcon = document.getElementById("challengeCtaIcon");
    if (challengeLink) {
      var showChallenge =
        window.ExpectUiTestRace &&
        ExpectUiTestRace.showChallengeCtaForRace &&
        ExpectUiTestRace.showChallengeCtaForRace(id);
      if (showChallenge) {
        challengeLink.hidden = false;
        challengeLink.href = ExpectUiTestRace.challengePurchaseHref(id);
        if (challengeIcon && ExpectUiTestRace.CHALLENGE_ICON_SVG) {
          challengeIcon.innerHTML = ExpectUiTestRace.CHALLENGE_ICON_SVG;
        }
      } else {
        challengeLink.hidden = true;
        challengeLink.removeAttribute("href");
      }
    }`;

const NEW_BIND = `    function applyChallengeCta(raceId) {
      var challengeLink = document.getElementById("challengePurchaseLink");
      if (!challengeLink) return;
      var catalog = window.ExpectCatalogIdentity;
      var href =
        catalog && typeof catalog.challengePurchaseHref === "function"
          ? catalog.challengePurchaseHref(raceId)
          : "";
      var show =
        !!href &&
        catalog &&
        typeof catalog.showChallengeCtaForRace === "function" &&
        catalog.showChallengeCtaForRace(raceId);
      if (show) {
        challengeLink.hidden = false;
        challengeLink.href = href;
        var challengeIcon = document.getElementById("challengeCtaIcon");
        if (
          challengeIcon &&
          window.ExpectUiTestRace &&
          ExpectUiTestRace.CHALLENGE_ICON_SVG
        ) {
          challengeIcon.innerHTML = ExpectUiTestRace.CHALLENGE_ICON_SVG;
        }
      } else {
        challengeLink.hidden = true;
        challengeLink.removeAttribute("href");
      }
    }
    applyChallengeCta(id);`;

const OLD_BOOT = `        var challengeLinkReady = document.getElementById("challengePurchaseLink");
        if (challengeLinkReady && window.ExpectUiTestRace) {
          if (ExpectUiTestRace.showChallengeCtaForRace(id)) {
            challengeLinkReady.hidden = false;
            challengeLinkReady.href = ExpectUiTestRace.challengePurchaseHref(id);
            var cico = document.getElementById("challengeCtaIcon");
            if (cico && ExpectUiTestRace.CHALLENGE_ICON_SVG) {
              cico.innerHTML = ExpectUiTestRace.CHALLENGE_ICON_SVG;
            }
          } else {
            challengeLinkReady.hidden = true;
          }
        }`;

const NEW_BOOT = `        applyChallengeCta(id);`;

function assetRefs(html) {
  return [...html.matchAll(/(?:src|href)="([^"]+\.(?:js|css)[^"]*)"/g)].map(
    (m) => m[1]
  );
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.prodPublic) {
    console.error("FAIL: --prod-public <dir> is required (current Production public/)");
    process.exit(2);
  }
  const prodPublic = path.resolve(args.prodPublic);
  const racePath = path.join(prodPublic, "race.html");
  const catPath = path.join(prodPublic, "assets/api/catalog-identity.js");
  const srcCat = path.join(ROOT, "public/assets/api/catalog-identity.js");

  if (!fs.existsSync(racePath) || !fs.existsSync(catPath)) {
    console.error("FAIL: race.html or assets/api/catalog-identity.js missing in", prodPublic);
    process.exit(2);
  }

  const beforeRaceRaw = fs.readFileSync(racePath, "utf8");
  const nl = beforeRaceRaw.includes("\r\n") ? "\r\n" : "\n";
  const beforeRace = beforeRaceRaw.replace(/\r\n/g, "\n");
  const beforeRefs = assetRefs(beforeRace);

  if (!beforeRace.includes("ExpectUiTestRace.showChallengeCtaForRace")) {
    if (beforeRace.includes("function applyChallengeCta")) {
      console.log("ALREADY_OVERLAID = YES");
      process.exit(0);
    }
    console.error("FAIL: unexpected race.html (no ui-test CTA bind, no applyChallengeCta)");
    process.exit(2);
  }
  if (!beforeRace.includes('assets/api/catalog-identity.js?v=2')) {
    console.error("FAIL: expected catalog-identity.js?v=2 in Production race.html");
    process.exit(2);
  }
  if (!beforeRace.includes(OLD_BIND) || !beforeRace.includes(OLD_BOOT)) {
    console.error("FAIL: CTA bind blocks do not match expected Production markup");
    process.exit(2);
  }

  let next = beforeRace.replace("assets/api/catalog-identity.js?v=2", "assets/api/catalog-identity.js?v=3");
  next = next.replace(OLD_BIND, NEW_BIND);
  next = next.replace(OLD_BOOT, NEW_BOOT);

  if (next.includes("ExpectUiTestRace.showChallengeCtaForRace")) {
    console.error("FAIL: ui-test CTA bind still present after overlay");
    process.exit(2);
  }
  if (!next.includes("function applyChallengeCta") || !next.includes("applyChallengeCta(id)")) {
    console.error("FAIL: applyChallengeCta not applied");
    process.exit(2);
  }

  const afterRefs = assetRefs(next);
  const beforeOther = beforeRefs.filter((r) => !r.includes("catalog-identity.js"));
  const afterOther = afterRefs.filter((r) => !r.includes("catalog-identity.js"));
  if (JSON.stringify(beforeOther) !== JSON.stringify(afterOther)) {
    console.error("FAIL: unrelated asset versions changed");
    console.error({ beforeOther, afterOther });
    process.exit(2);
  }

  fs.copyFileSync(srcCat, catPath);
  const outRace = nl === "\r\n" ? next.replace(/\n/g, "\r\n") : next;
  fs.writeFileSync(racePath, outRace, "utf8");

  const catalog = fs.readFileSync(catPath, "utf8");
  const report = {
    OVERLAY_APPLIED: "YES",
    FILES_WRITTEN: ["race.html", "assets/api/catalog-identity.js"],
    CATALOG_HAS_SHOW_CHALLENGE: catalog.includes("function showChallengeCtaForRace"),
    RACE_HTML_CATALOG_REF: (next.match(/catalog-identity\.js[^"']*/) || [])[0] || "",
    UNRELATED_ASSET_VERSIONS_CHANGED: "NO",
    DEPLOY_EXECUTED: "NO",
    NOTE: "Deploy the Production public dir after overlay. Do not deploy git public/.",
  };
  console.log(JSON.stringify(report, null, 2));
}

main();
