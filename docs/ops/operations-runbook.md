# 運用 Runbook — Expect KEIBA AI（v1.0.0-stable）

**Baseline:** tag `v1.0.0-stable` / commit `08c7986`  
**関連:** [`stable-baseline-v1.0.0.md`](./stable-baseline-v1.0.0.md) · [`known-issues-v1.0.0-stable.md`](./known-issues-v1.0.0-stable.md) · [`rollback-runbook.md`](../rollback-runbook.md)

本番ホスト例:

| 面 | 例 |
|----|-----|
| Pages | `https://expect-keiba.com` |
| AI（Tunnel） | `https://ai.expect-keiba.com` |
| EC2 アプリ | `/home/ubuntu/KEIBA-Single-AI` |
| Platform | `/opt/expect-ai/platform`（`AI_PLATFORM_ROOT`） |
| Env | `/opt/expect-ai/shared/.env` |
| systemd | `expect-ai.service` / `cloudflared-expect-ai.service` |

---

## 0. 運用フェーズの原則

1. **Stable Baseline を壊さない**（予想ロジック既定・Flag 既定を勝手に変えない）
2. デプロイは **Git → Pages（自動）+ EC2（手動 pull）+ overlay 同期 + migrate + restart**
3. **Collector Real KeibaNet は HOLD**（本接続ジョブを本番で回さない）
4. **Feature Flag は OFF 維持**（特に `WIN5_REPICK_V2_ENABLED`）

---

## 1. デプロイ手順

### 1.1 事前

- [ ] 反映する commit / tag を記録（rollback 用）
- [ ] DB / `.env` バックアップ
- [ ] Pages secrets（`AI_BASE_URL`, `AI_API_KEY`, Access Token, `OPS_MONITOR_KEY`）確認
- [ ] `.env` に `WIN5_REPICK_V2_ENABLED` が無いこと

### 1.2 Cloudflare Pages（GUI + BFF + 招待 seed）

1. `main` へ push（または tag 追従）
2. Pages Production Deployment が対象 commit になるまで待つ
3. 確認:
   - `GET https://expect-keiba.com/api/health` → 200
   - `GET https://expect-keiba.com/data/invitations.json`（必要 ID が含まれること）

招待 ID を `public/data/invitations.json` に追加した場合は **Pages 再デプロイ必須**。

### 1.3 EC2（Python AI）

```bash
cd /home/ubuntu/KEIBA-Single-AI
git fetch --tags origin
git checkout v1.0.0-stable   # または git checkout 08c7986 / 承認済み SHA
```

続けて **§2 overlay → §3 migrate → §4 restart** の順で実施。

### 1.4 デプロイ後スモーク（短縮）

- [ ] `curl -sS https://ai.expect-keiba.com/health` → `status=ok`
- [ ] 一時ID or 既存ログインで UI 到達
- [ ] `GET /api/predictions` → 200（`provider=python`）
- [ ] Flag / KeibaNet HOLD が崩れていない（§6 / §7）

---

## 2. overlay 同期手順（必須）

### なぜ必要か

`run.py` は起動時に `platform/core-overlay` を `AI_PLATFORM_ROOT` へコピーする想定だが、  
`from app.core.platform_overlay ...` の import 経路で **overlay 適用前に `feature_loader` が必要**になり、未同期だと:

`ModuleNotFoundError: No module named 'ai_platform.core.features.feature_loader'`

で `expect-ai` が起動失敗する（v1.0.0-stable 本番反映時に確認済み）。

### 手順

```bash
# EC2
SRC=/home/ubuntu/KEIBA-Single-AI/services/win5-ai/platform/core-overlay/ai_platform
DST=/opt/expect-ai/platform/ai_platform

test -d "$SRC" && test -d "$DST"
cp -a "$SRC"/. "$DST"/

# 確認
python3 - <<'PY'
import sys
sys.path.insert(0, "/opt/expect-ai/platform")
from ai_platform.core.features.feature_loader import FeatureLoadResult
print("overlay OK", FeatureLoadResult)
PY
```

**タイミング:** `git pull` / `checkout` の直後、**migrate / restart の前**に実施。

---

## 3. migrate 手順

```bash
cd /home/ubuntu/KEIBA-Single-AI/services/win5-ai
set -a
. /opt/expect-ai/shared/.env
set +a
export PYTHONPATH=/opt/expect-ai/platform:${PYTHONPATH:-}

python3 -m app.data.import_csv migrate
```

成功時:

- 新規適用があれば migration 名が列挙される
- 既適用のみなら `applied []`

確認（任意）:

```bash
sqlite3 "$EXPECT_AI_DB_PATH" "SELECT * FROM schema_migrations ORDER BY 1;"
```

v1.0.0-stable 期待: `001_init` … `008_collect_contract_1_1`

---

## 4. restart 手順

```bash
sudo systemctl restart expect-ai
sleep 3
systemctl is-active expect-ai
curl -sS http://127.0.0.1:8000/health
sudo journalctl -u expect-ai -n 50 --no-pager
```

期待:

- `active`
- JSON `status: "ok"`
- v1.0.0-stable 以降は `result_automation` キーあり

Tunnel 側（通常は無停止）:

```bash
systemctl is-active cloudflared-expect-ai
```

問題時のみ:

```bash
sudo systemctl restart cloudflared-expect-ai
```

---

## 5. rollback 手順

### 5.1 Pages

1. Cloudflare Dashboard → Pages → `keiba-single-ai` → Deployments
2. 直前の Success Deployment を **Rollback**
3. `/api/health` とログイン画面を確認

緊急時は `maintenance_mode: true`（`config/beta.json` + `public/config/beta.json` 同期 → 再デプロイ）。詳細は [`../rollback-runbook.md`](../rollback-runbook.md)。

### 5.2 EC2 / AI

```bash
cd /home/ubuntu/KEIBA-Single-AI
# 例: Stable Baseline に戻す
git fetch --tags origin
git checkout v1.0.0-stable

# overlay → migrate（前方互換のみ注意）→ restart
# （§2 → §3 → §4）
```

**DB:** migration は基本前方適用。ダウングレードで schema が合わない場合は **バックアップからのリストア**を優先（勝手に DROP しない）。

### 5.3 記録

Rollback 実施後、戻した SHA/tag・理由・時刻をインシデントログへ残す。

---

## 6. Feature Flag 運用ルール

| Flag | v1.0.0-stable 既定 | 本番ルール |
|------|-------------------|------------|
| `WIN5_REPICK_V2_ENABLED` | **OFF**（未設定 / false） | **設定禁止**。研究のみ `research/repick-v2/` |
| `WIN5_REPICK_V2_SLOT` / `RANK6` | OFF | 同上 |
| `AI_ENGINE` | `real` | 観測用。mock 固定への無断切替禁止 |
| `AUTH_MODE` | `stub`（現行） | 変更は別リリース承認 |
| `VALIDATE_CONTRACTS` | `soft` | 同上 |

ルール:

1. 本番 `.env` / Pages vars に RePick 系を **書かない**
2. Flag ON は **Exit Criteria 全合格 + 明示リリース**が条件（現状未達）
3. コード上の研究スナップショットがあっても **製品既定は identity（無変更）**
4. Hit率改善トラックは停止中。再開は Version 1.1 Backlog の承認後

確認コマンド（EC2）:

```bash
grep -i REPICK /opt/expect-ai/shared/.env || echo "OK: no REPICK flags"
test ! -f /opt/expect-ai/platform/v2_repick_v2.py && echo "OK: not wired on platform"
```

---

## 7. Collector / Real KeibaNet — HOLD

**方針（v1.0.0-stable）: Real KeibaNet 本接続は HOLD**

| やってよい | やってはいけない |
|------------|------------------|
| RC-1 コードの保持・単体/Controlled 検証の計画 | `EXPECT_KEIBANET_BASE_URL` を本番 `.env` に入れて常時収集 |
| docs 上の O-1 検証プラン整備 | systemd で本番 Collector を Real 向けに enable |
| | Go-Live 宣言（Real 接続検証完了前） |

確認:

```bash
grep -iE 'KEIBANET|COLLECT' /opt/expect-ai/shared/.env || echo "OK: no KeibaNet collect config"
systemctl list-timers --all | grep -iE 'collect|result' || true
ps aux | grep -iE 'collect|keibanet' | grep -v grep || echo "OK: no collector process"
```

解除条件: [`collector-o1-real-keibanet-validation-plan.md`](./collector-o1-real-keibanet-validation-plan.md) 完了 + 明示 GO。

---

## 8. 日常監視（要約）

**正本（v1.0 運用監視設計）:** [`v1.0-ops-monitoring-design.md`](./v1.0-ops-monitoring-design.md)  
**月次テンプレ:** [`monthly-ops-report-template.md`](./monthly-ops-report-template.md)

- Pages: Deployment Success / `/api/health`
- AI: `/health` + `journalctl -u expect-ai`
- 予想: `provider=python`、意図しない全面断を監視（`mock_fallback` 比率は Known Issues 参照）
- 招待: 発行は `npm run beta`、seed 反映は Pages デプロイ

詳細（既存実装）: [`ops-monitor.md`](./ops-monitor.md) · [`monitoring.md`](./monitoring.md)

---

## 9. 連絡・エスカレーション

| 症状 | 第一手 |
|------|--------|
| AI 起動失敗 / feature_loader | §2 overlay → §4 restart |
| ログイン不可 | Pages Rollback / 招待 JSON / メンテ |
| 予想全滅 | AI health、Tunnel、`AI_BASE_URL` |
| 不正アクセス疑い | メンテ ON + Access 縮小（[`../rollback-runbook.md`](../rollback-runbook.md)） |
