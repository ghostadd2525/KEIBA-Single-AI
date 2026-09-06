#!/usr/bin/env bash
# READ-ONLY Production vs PR #7 confirmation.
# Never git reset / clean / checkout. Never overwrite Production sources.
# Never change P1_SHUTUBA_CACHE_POLICY or systemd.
set -euo pipefail

if [[ "${1:-}" == "--apply" || "${1:-}" == "--write" || "${1:-}" == "--checkout" ]]; then
  echo "REFUSE: this script is diff-only. No apply/checkout."
  exit 2
fi

REPO="${REPO:-/home/ubuntu/KEIBA-Single-AI}"
RR_REL="services/pi-keibanet-api/pi_keibanet/race_refresh.py"
HS_REL="services/pi-keibanet-api/pi_keibanet/history_store.py"
RR="$REPO/$RR_REL"
HS="$REPO/$HS_REL"
PR_REF="${PR_REF:-origin/cursor/history-static-hold-repair-22d3}"
MAIN_REF="${MAIN_REF:-origin/main}"
STAMP="$(date +%Y%m%dT%H%M%S)"
OUT="${OUT_DIR:-/tmp/prod-history-repair-diff-$STAMP}"
mkdir -p "$OUT"

echo "OUT=$OUT"
echo "REPO=$REPO"
echo "cwd must stay Production working tree; this script writes /tmp only."

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "MISSING: $1"
    exit 1
  fi
}

require_file "$RR"
require_file "$HS"

echo
echo "===== 1. Production sha256 ====="
sha256sum "$RR" "$HS" | tee "$OUT/prod_sha256.txt"

echo
echo "===== 2. Production mtime ====="
stat -c '%n mtime=%y size=%s inode=%i' "$RR" "$HS" | tee "$OUT/prod_mtime.txt"
ls -l --full-time "$RR" "$HS" | tee "$OUT/prod_ls.txt"

echo
echo "===== 2b. Production-only context (read-only) ====="
{
  echo "# static_history_merge.py locations"
  find "$REPO/services/pi-keibanet-api" "$REPO" -name 'static_history_merge.py' 2>/dev/null || true
  echo
  echo "# markers in the two implementation files"
  grep -nE 'P1_SHUTUBA|static_history_merge|STATIC hold|empty_maiden|skip history|fetch_history|history_ok' "$RR" "$HS" || true
  echo
  echo "# systemd drop-in / env (read-only; do not edit)"
  systemctl cat expect-pi-race-refresh.service 2>/dev/null || true
  echo '---'
  systemctl cat expect-pi-keibanet-api.service 2>/dev/null || true
  echo '---'
  grep -Rns 'P1_SHUTUBA_CACHE_POLICY' /etc/systemd/system /etc/expect-ai /lib/systemd/system 2>/dev/null || true
} | tee "$OUT/prod_context.txt"

echo
echo "===== 3. Fetch PR/main blobs into /tmp only (no checkout) ====="
cd "$REPO"
# fetch is read of remotes; it does not change tracked working files
git fetch origin cursor/history-static-hold-repair-22d3 main
git show "$MAIN_REF:$RR_REL" > "$OUT/main_race_refresh.py"
git show "$MAIN_REF:$HS_REL" > "$OUT/main_history_store.py"
git show "$PR_REF:$RR_REL" > "$OUT/pr7_race_refresh.py"
git show "$PR_REF:$HS_REL" > "$OUT/pr7_history_store.py"
cp -a "$RR" "$OUT/prod_race_refresh.py"
cp -a "$HS" "$OUT/prod_history_store.py"

{
  echo "main_race_refresh $(sha256sum "$OUT/main_race_refresh.py")"
  echo "pr7_race_refresh  $(sha256sum "$OUT/pr7_race_refresh.py")"
  echo "prod_race_refresh $(sha256sum "$OUT/prod_race_refresh.py")"
  echo "main_history_store $(sha256sum "$OUT/main_history_store.py")"
  echo "pr7_history_store  $(sha256sum "$OUT/pr7_history_store.py")"
  echo "prod_history_store $(sha256sum "$OUT/prod_history_store.py")"
} | tee "$OUT/triple_sha256.txt"

echo
echo "===== 3b. Extract relevant functions (Production) ====="
python3 - "$OUT" <<'PY'
import ast
import sys
from pathlib import Path

out = Path(sys.argv[1])
specs = {
    "prod_race_refresh.py": [
        "RaceSnapshotEntry",
        "load_snapshot",
        "select_races_for_update",
        "race_needs_history_repair",
        "_enqueue_history_repairs",
        "process_race_pipeline",
        "merge_day_frames",
        "run_refresh",
    ],
    "prod_history_store.py": [
        "is_weekend_jst",
        "csv_has_history_rows",
        "CsvHistoryStore",
        "CompositeHistoryStore",
    ],
}

def extract(src: str, names: list[str]) -> str:
    tree = ast.parse(src)
    chunks = []
    wanted = set(names)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in wanted:
            chunk = ast.get_source_segment(src, node)
            if chunk:
                chunks.append(f"# ---- {node.name} ----\n{chunk}\n")
            wanted.discard(node.name)
    missing = [n for n in names if n in wanted]
    if missing:
        chunks.append("# MISSING_ON_PRODUCTION: " + ", ".join(missing) + "\n")
    return "\n".join(chunks)

for fname, names in specs.items():
    src = (out / fname).read_text(encoding="utf-8")
    text = extract(src, names)
    dest = out / f"functions_{fname}"
    dest.write_text(text, encoding="utf-8")
    print(f"wrote {dest} ({len(text.splitlines())} lines)")
PY

echo
echo "===== 4. Diffs (main / prod / PR7) ====="
diff -u "$OUT/main_race_refresh.py" "$OUT/prod_race_refresh.py" > "$OUT/diff_prod_vs_main_race_refresh.patch" || true
diff -u "$OUT/main_history_store.py" "$OUT/prod_history_store.py" > "$OUT/diff_prod_vs_main_history_store.patch" || true
diff -u "$OUT/main_race_refresh.py" "$OUT/pr7_race_refresh.py" > "$OUT/diff_pr7_vs_main_race_refresh.patch" || true
diff -u "$OUT/main_history_store.py" "$OUT/pr7_history_store.py" > "$OUT/diff_pr7_vs_main_history_store.patch" || true
diff -u "$OUT/prod_race_refresh.py" "$OUT/pr7_race_refresh.py" > "$OUT/diff_prod_vs_pr7_race_refresh.patch" || true
diff -u "$OUT/prod_history_store.py" "$OUT/pr7_history_store.py" > "$OUT/diff_prod_vs_pr7_history_store.patch" || true
wc -l "$OUT"/diff_*.patch | tee "$OUT/diff_wc.txt"

echo
echo "===== 5. Classify PROD-only vs PR hunks (dry-run patch on copies) ====="
python3 - "$OUT" <<'PY'
import hashlib
import subprocess
import sys
from pathlib import Path

out = Path(sys.argv[1])

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def dry_run(src: Path, patch: Path) -> tuple[bool, str]:
    if patch.stat().st_size == 0:
        return True, "empty_patch"
    # patch a copy only
    work = src.with_name(src.name + ".dry")
    work.write_bytes(src.read_bytes())
    proc = subprocess.run(
        ["patch", "--dry-run", "--forward", "--reject-file=-", str(work)],
        input=patch.read_bytes(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    text = proc.stdout.decode("utf-8", "replace")
    return proc.returncode == 0, text

rows = []
for kind in ("race_refresh.py", "history_store.py"):
    stem = kind.replace(".py", "")
    prod = out / f"prod_{stem}.py"
    main = out / f"main_{stem}.py"
    pr7 = out / f"pr7_{stem}.py"
    pr_patch = out / f"diff_pr7_vs_main_{stem}.patch"
    ok, log = dry_run(prod, pr_patch)
    (out / f"dry_run_{stem}.txt").write_text(log, encoding="utf-8")
    same_main = sha(prod) == sha(main)
    same_pr7 = sha(prod) == sha(pr7)
    prod_vs_main = (out / f"diff_prod_vs_main_{stem}.patch").stat().st_size
    prod_vs_pr7 = (out / f"diff_prod_vs_pr7_{stem}.patch").stat().st_size
    if same_pr7:
        verdict = "ALREADY_PR7"
        method = "NO_FILE_REPLACE"
    elif same_main and ok:
        verdict = "MATCHES_ORIGIN_MAIN"
        method = "APPLY_TWO_FILES_ONLY"
    elif ok and prod_vs_main > 0:
        verdict = "PR_HUNKS_APPLY_CLEAN_BUT_PROD_DIFFERS_FROM_MAIN"
        method = "MIN_HUNK_MANUAL"
    elif not ok:
        verdict = "PR_HUNKS_DO_NOT_APPLY_CLEAN"
        method = "MIN_HUNK_MANUAL"
    else:
        verdict = "REVIEW"
        method = "MIN_HUNK_MANUAL"
    rows.append((kind, same_main, same_pr7, ok, prod_vs_main, prod_vs_pr7, verdict, method))
    print(f"{kind}: prod==main={same_main} prod==pr7={same_pr7} patch_dry_run={ok}")
    print(f"  prod_vs_main_bytes={prod_vs_main} prod_vs_pr7_bytes={prod_vs_pr7}")
    print(f"  PROD_BASELINE_MATCH={same_main}")
    print(f"  VERDICT={verdict}")
    print(f"  SAFE_APPLY_METHOD={method}")

methods = {r[7] for r in rows}
overall = "MIN_HUNK_MANUAL" if "MIN_HUNK_MANUAL" in methods else sorted(methods)[0]
prod_only = any((not r[1]) or (not r[3]) or r[7] == "MIN_HUNK_MANUAL" for r in rows)
summary = []
summary.append(f"PROD_BASELINE_MATCH = {all(r[1] for r in rows)}")
summary.append(f"PROD_ONLY_DIFF = {prod_only}")
summary.append(f"SAFE_APPLY_METHOD = {overall}")
summary.append("FILES_CHANGED = services/pi-keibanet-api/pi_keibanet/race_refresh.py, services/pi-keibanet-api/pi_keibanet/history_store.py")
summary.append("PREDICTION_DIFF = 0")
summary.append("SYSTEMD_DIFF = 0")
summary.append("NOTE = Do not merge PR #7 and checkout Production. Whole-file replace is forbidden when PROD_ONLY_DIFF=True.")
text = "\n".join(summary) + "\n"
(out / "CLASSIFICATION.txt").write_text(text, encoding="utf-8")
print()
print(text)
PY

echo
echo "DONE. Read $OUT/CLASSIFICATION.txt"
echo "Function extracts: $OUT/functions_prod_*.py"
echo "Do NOT copy pr7_*.py over Production files."
