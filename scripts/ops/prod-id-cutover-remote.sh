#!/usr/bin/env bash
# PROD-PREDICTION-ID-CUTOVER-OWNER-LOCAL
# Run ON production EC2 (piped via Windows SSH). Touches only Catalog/Core ID contract files.
# Never overwrites prediction_adapter.py. Never restarts tunnel/BFF. Never runs ETL/Feature.
set -euo pipefail

REPO="${REPO:-/home/ubuntu/KEIBA-Single-AI}"
BRANCH_REF="${BRANCH_REF:-origin/cursor/race-id-contract-22d3}"
FETCH_REF="${FETCH_REF:-cursor/race-id-contract-22d3}"
LOCALHOST="${LOCALHOST:-http://127.0.0.1:8000}"
TARGET_ID="2026-08-16-03-10"
TARGET_CORE="2026-08-16-01-10"
CONTROL_ID="2026-07-25-01-05"
CONTROL_TOP1_NAME="キシダンチョウ"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="/opt/expect-ai/backups/id-cutover-${STAMP}"
REPORT="/tmp/id-cutover-${STAMP}-report.txt"
ADAPTER_REL="services/win5-ai/app/engine/adapters/prediction_adapter.py"

FILES=(
  "services/win5-ai/app/data/race_resolver.py"
  "services/win5-ai/app/data/catalog_index.py"
  "services/win5-ai/app/data/catalog_fixtures/2026-08-16.json"
)

log() { printf '[id-cutover] %s\n' "$*"; }
die() { printf '[id-cutover] ERROR: %s\n' "$*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

sha_of() {
  if [[ -f "$1" ]]; then
    sha256sum "$1" | awk '{print $1}'
  else
    echo "MISSING"
  fi
}

curl_json() {
  local url="$1"
  local timeout="${2:-45}"
  curl -sS --max-time "$timeout" "$url"
}

rollback() {
  log "ROLLBACK from ${BACKUP}"
  [[ -d "$BACKUP" ]] || die "backup dir missing: $BACKUP"
  cd "$REPO"
  for rel in "${FILES[@]}"; do
    local bak="${BACKUP}/$(basename "$rel")"
    local dest="${REPO}/${rel}"
    if [[ -f "$bak" ]]; then
      mkdir -p "$(dirname "$dest")"
      cp -a "$bak" "$dest"
      log "restored $rel"
    else
      if [[ -f "$dest" && "$(basename "$rel")" != "race_resolver.py" ]]; then
        rm -f "$dest"
        log "removed newly added $rel"
      fi
    fi
  done
  sudo systemctl restart expect-ai
  sleep 4
  systemctl is-active expect-ai | grep -qx active || die "expect-ai not active after rollback"
  curl -sf --max-time 8 "${LOCALHOST}/health" >/dev/null || die "health failed after rollback"
  log "rollback complete"
}

on_fail() {
  local rc=$?
  if [[ "${CUTOVER_DONE:-0}" == "1" ]]; then
    exit "$rc"
  fi
  log "failure rc=${rc}; attempting rollback"
  rollback || true
  exit "$rc"
}

trap on_fail ERR

need_cmd git
need_cmd curl
need_cmd python3
need_cmd sha256sum
need_cmd systemctl
[[ -d "$REPO" ]] || die "repo not found: $REPO"
cd "$REPO"

log "PREDEPLOY runtime"
hostname
pwd
git rev-parse --short HEAD || true
git status --porcelain | head || true
systemctl is-active expect-ai || true
systemctl is-active cloudflared-expect-ai || true
curl -sS --max-time 8 "${LOCALHOST}/health" | head -c 400 || true
echo

log "PREDEPLOY hashes"
ADAPTER_SHA_BEFORE="$(sha_of "${REPO}/${ADAPTER_REL}")"
declare -A SHA_BEFORE
for rel in "${FILES[@]}"; do
  SHA_BEFORE["$rel"]="$(sha_of "${REPO}/${rel}")"
  log "BEFORE $rel ${SHA_BEFORE[$rel]}"
done
log "BEFORE adapter ${ADAPTER_SHA_BEFORE}"

sudo mkdir -p "$BACKUP"
sudo chown ubuntu:ubuntu "$BACKUP"
for rel in "${FILES[@]}"; do
  if [[ -f "${REPO}/${rel}" ]]; then
    cp -a "${REPO}/${rel}" "${BACKUP}/$(basename "$rel")"
  fi
done
# hash-only record of dirty adapter; file itself is NOT restored unless we touched it
printf '%s\n' "$ADAPTER_SHA_BEFORE" > "${BACKUP}/prediction_adapter.py.sha256"
log "backup ${BACKUP}"

log "PREDEPLOY target/control BEFORE"
mkdir -p "${BACKUP}/http"
curl_json "${LOCALHOST}/v1/predictions/${TARGET_ID}" 60 > "${BACKUP}/http/target-before.json" || true
curl_json "${LOCALHOST}/v1/races/resolve?text=${TARGET_ID}" 20 > "${BACKUP}/http/target-resolve-before.json" || true
curl_json "${LOCALHOST}/v1/predictions/${CONTROL_ID}" 90 > "${BACKUP}/http/control-before.json" || true

python3 - "$BACKUP" "$CONTROL_TOP1_NAME" <<'PY'
import json, sys
bak = sys.argv[1]
expect_top1 = sys.argv[2]
def load(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception as e:
        return {"_error": str(e)}
t = load(f"{bak}/http/target-before.json")
meta = t.get("meta") or {}
print("TARGET_BEFORE_FALLBACK", meta.get("fallback_reason"), meta.get("detail"))
c = load(f"{bak}/http/control-before.json")
cm = c.get("meta") or {}
ri = ((c.get("data") or {}).get("race_info") or {})
runners = ((c.get("data") or {}).get("evaluation") or {}).get("runners") or []
top = sorted([r for r in runners if r.get("model_rank") is not None], key=lambda r: r.get("model_rank") or 999)
top1 = (top[0].get("horse_name") if top else None)
print("CONTROL_BEFORE", cm.get("decision_authority"), cm.get("engine_source"), ri.get("venue"), ri.get("race_no"), top1)
if cm.get("decision_authority") != "RESTORED_V2":
    sys.exit("control is not RESTORED_V2 before deploy; abort")
if ri.get("venue") != "新潟" or int(ri.get("race_no") or 0) != 5:
    sys.exit("control is not 新潟5R before deploy; abort")
if top1 != expect_top1:
    sys.exit(f"control top1 changed before deploy: {top1!r} != {expect_top1!r}")
open(f"{bak}/control-top1.txt","w",encoding="utf-8").write(top1 or "")
PY

log "DEPLOY fetch ${FETCH_REF}"
git fetch origin "$FETCH_REF"
git rev-parse "$BRANCH_REF" >/dev/null

log "DEPLOY checkout 3 files only"
git checkout "$BRANCH_REF" -- "${FILES[@]}"

# prove adapter untouched
ADAPTER_SHA_MID="$(sha_of "${REPO}/${ADAPTER_REL}")"
[[ "$ADAPTER_SHA_MID" == "$ADAPTER_SHA_BEFORE" ]] || die "prediction_adapter.py hash changed during checkout"

log "py_compile"
python3 -m py_compile \
  "${REPO}/services/win5-ai/app/data/catalog_index.py" \
  "${REPO}/services/win5-ai/app/data/race_resolver.py"

log "DEPLOYED hashes"
declare -A SHA_AFTER
for rel in "${FILES[@]}"; do
  SHA_AFTER["$rel"]="$(sha_of "${REPO}/${rel}")"
  log "AFTER $rel ${SHA_AFTER[$rel]}"
  [[ "${SHA_AFTER[$rel]}" != "MISSING" ]] || die "missing after deploy: $rel"
done
ADAPTER_SHA_AFTER="$(sha_of "${REPO}/${ADAPTER_REL}")"
log "AFTER adapter ${ADAPTER_SHA_AFTER}"
[[ "$ADAPTER_SHA_AFTER" == "$ADAPTER_SHA_BEFORE" ]] || die "adapter hash mismatch"

log "unrelated files: git status for adapter must be unchanged vs pre-checkout adapter"
# restart expect-ai ONLY
log "restart expect-ai"
sudo systemctl restart expect-ai
sleep 5
systemctl is-active expect-ai | grep -qx active || die "expect-ai not active"
# tunnel must still be whatever it was; we do not restart it
curl -sf --max-time 10 "${LOCALHOST}/health" >/dev/null || die "local health failed"

log "POSTDEPLOY target"
curl_json "${LOCALHOST}/v1/predictions/${TARGET_ID}" 60 > "${BACKUP}/http/target-after.json"
curl_json "${LOCALHOST}/v1/races/resolve?text=${TARGET_ID}" 20 > "${BACKUP}/http/target-resolve-after.json"

python3 - "$BACKUP" "$TARGET_ID" "$TARGET_CORE" <<'PY'
import json, sys
bak, target, core = sys.argv[1], sys.argv[2], sys.argv[3]
ident = json.load(open(f"{bak}/http/target-resolve-after.json", encoding="utf-8"))
if ident.get("ok") is not True:
    sys.exit(f"resolve failed: {ident}")
data = ident.get("data") or {}
venue = data.get("venue")
race_no = int(data.get("race_no") or 0)
core_id = data.get("core_race_id")
print("RESOLVE", venue, race_no, core_id, data.get("id_namespace"), data.get("catalog_race_id"))
if venue != "札幌" or race_no != 10:
    sys.exit(f"venue/race mismatch: {venue} {race_no}")
if core_id != core:
    sys.exit(f"core mismatch: {core_id}")
pred = json.load(open(f"{bak}/http/target-after.json", encoding="utf-8"))
meta = pred.get("meta") or {}
reason = str(meta.get("fallback_reason") or "")
detail = str(meta.get("detail") or "")
print("PRED_META", json.dumps({k: meta.get(k) for k in (
    "fallback_reason","detail","source_race_id","canonical_race_id","core_race_id",
    "engine_source","decision_authority","race_type","fallback_state","feature_lookup_key"
)}, ensure_ascii=False))
if reason == "race_not_found" or "no resolvable core race_id" in detail:
    sys.exit("still race_not_found")
feature_ok = reason in (
    "market_feature_missing", "feature_csv_missing", "feature_missing", "platform_missing"
)
if not feature_ok:
    # allow missing reason only if core is present and not RESTORED_V2
    if not meta.get("core_race_id") and not meta.get("canonical_race_id"):
        sys.exit(f"unexpected fallback {reason!r}")
if str(meta.get("decision_authority") or "") == "RESTORED_V2":
    sys.exit("RESTORED_V2 reached on target; unexpected")
core_got = meta.get("core_race_id") or meta.get("canonical_race_id")
# dirty adapter may put venue-qualified in canonical; core_race_id must be the Core id
if meta.get("core_race_id") and meta.get("core_race_id") != core:
    sys.exit(f"pred core mismatch {meta.get('core_race_id')}")
open(f"{bak}/target-ok.txt","w",encoding="utf-8").write(
    f"{venue}\t{race_no}\t{core_id}\t{reason}\n"
)
PY

log "36R mapping sanity via running resolver HTTP"
python3 - "$LOCALHOST" "$BACKUP" <<'PY'
import json, sys, urllib.request
base = sys.argv[1]
bak = sys.argv[2]
date = "2026-08-16"
meetings = [
    ("新潟", "01", "04"),
    ("中京", "02", "07"),
    ("札幌", "03", "01"),
]
rows = []
for course, label, jra in meetings:
    for n in range(1, 13):
        cid = f"{date}-{label}-{n:02d}"
        url = f"{base}/v1/races/resolve?text={cid}"
        with urllib.request.urlopen(url, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if not body.get("ok"):
            raise SystemExit(f"resolve fail {cid}: {body}")
        d = body.get("data") or {}
        rows.append((cid, d))
        if d.get("venue") != course:
            raise SystemExit(f"venue {cid}: {d.get('venue')} != {course}")
        if int(d.get("race_no") or 0) != n:
            raise SystemExit(f"race_no {cid}: {d.get('race_no')} != {n}")
        core = str(d.get("core_race_id") or "")
        parts = core.split("-")
        if len(parts) < 5 or parts[3] != jra:
            raise SystemExit(f"core venue {cid} -> {core} expected JRA {jra}")
        if int(parts[4]) != n:
            raise SystemExit(f"core race {cid} -> {core}")
ids = [c for c,_ in rows]
cores = [d.get("core_race_id") for _,d in rows]
if len(set(ids)) != 36:
    raise SystemExit("source ids not unique")
if len(set(cores)) != 36:
    raise SystemExit("core ids not unique")
# contamination: catalog course vs resolved venue
cont = sum(1 for (cid,d), (course,_,_) in zip(rows, [(c,l,j) for c,l,j in meetings for _ in range(12)]) if d.get("venue") != course)
# zip above is wrong length alignment — recompute simply
cont = 0
i = 0
for course, label, jra in meetings:
    for n in range(1, 13):
        _cid, d = rows[i]
        i += 1
        if d.get("venue") != course:
            cont += 1
if cont != 0:
    raise SystemExit(f"cross-venue contamination={cont}")
print("MAP36_OK unique_source=36 unique_core=36 contamination=0")
json.dump({"ids": ids, "cores": cores}, open(f"{bak}/http/map36.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
PY

log "CONTROL regression"
curl_json "${LOCALHOST}/v1/predictions/${CONTROL_ID}" 90 > "${BACKUP}/http/control-after.json"
python3 - "$BACKUP" "$CONTROL_TOP1_NAME" <<'PY'
import json, sys
bak, expect_top1 = sys.argv[1], sys.argv[2]
c = json.load(open(f"{bak}/http/control-after.json", encoding="utf-8"))
cm = c.get("meta") or {}
ri = ((c.get("data") or {}).get("race_info") or {})
runners = ((c.get("data") or {}).get("evaluation") or {}).get("runners") or []
top = sorted([r for r in runners if r.get("model_rank") is not None], key=lambda r: r.get("model_rank") or 999)
top1 = top[0].get("horse_name") if top else None
print("CONTROL_AFTER", cm.get("decision_authority"), cm.get("engine_source"), ri.get("venue"), ri.get("race_no"), top1)
if cm.get("decision_authority") != "RESTORED_V2":
    sys.exit("control lost RESTORED_V2")
if cm.get("engine_source") != "real_ai":
    sys.exit(f"control engine_source={cm.get('engine_source')}")
if ri.get("venue") != "新潟" or int(ri.get("race_no") or 0) != 5:
    sys.exit("control venue/race changed")
if top1 != expect_top1:
    sys.exit(f"control top1 changed: {top1!r}")
print("CONTROL_OK")
PY

CUTOVER_DONE=1
trap - ERR

{
  echo "VERDICT=ID_CUTOVER_PASS_NEXT_FEATURE"
  echo "BACKUP_PATH=${BACKUP}"
  echo "DEPLOYED_FILES=${FILES[*]}"
  for rel in "${FILES[@]}"; do
    echo "HASH_BEFORE_${rel}=${SHA_BEFORE[$rel]}"
    echo "HASH_AFTER_${rel}=${SHA_AFTER[$rel]}"
  done
  echo "ADAPTER_HASH_BEFORE=${ADAPTER_SHA_BEFORE}"
  echo "ADAPTER_HASH_AFTER=${ADAPTER_SHA_AFTER}"
  echo "PREDICTION_ADAPTER_TOUCHED=NO"
  echo "PRODUCTION_CHANGED=YES"
  echo "ROLLBACK_REQUIRED=NO"
  echo "RESTORED_V2_REACHED=NO"
  echo "FEATURE_READY=NO"
  echo "NEXT_BLOCKER=INPUT_DATA_NOT_READY"
  echo "CONTROL_REGRESSION=PASS"
  echo "MAP36=PASS"
} | tee "$REPORT"
log "report ${REPORT}"
log "PASS"
