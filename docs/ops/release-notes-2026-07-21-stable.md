# Release Notes — Stable Production Package (2026-07-21)

**Tag / 通称:** `stable-2026-07-21`（Collector RC-1 + GUI + 一時ID + 運用）  
**リポジトリ:** `KEIBA-Single-AI` (`main`)  
**予想ロジック変更:** **なし**（RePick V2 Feature Flag **OFF** 維持）

---

## Summary

本番向けに、以下の安定成果をまとめて反映する準備完了パッケージです。

| 領域 | 内容 | 状態 |
|------|------|------|
| Collector RC-1 | Weekday Collector C-0…C-8、Contract 1.1、Budget/Retry/分散、Manifest/Gate/OPS | **RC-1 PASS**（Real KeibaNet 本接続は HOLD） |
| GUI | Invitation Beta UI / P0–P2 UI 修正（既存 commit 含む） | 同梱 |
| 一時IDログイン | `invitations.json` + `npm run beta` 発行フロー | 同梱（`BETA-F6D1-E07E` 発行済み） |
| 運用機能 | Result Automation / OPS Monitor / Miss Evidence / Recovery | 同梱 |
| RePick V2 | 研究コード保持・Flag OFF・本番経路に載せない | **OFF（Hit率改善は停止）** |

---

## Included

### Collector RC-1
- `services/win5-ai/app/data/collect/`（planner / queue / scheduler / collector / budget / retry / friday_gate / ops_monitor 等）
- Migrations `007_collect_c0.sql` / `008_collect_contract_1_1.sql`
- Contract `expect-collect-week-manifest/1.1`
- 検証ドキュメント: `docs/ops/collector-rc1-release-review.md` ほか C7/C8

### GUI / Auth（一時ID）
- Pages 静的面 `public/`（既存 UI 改善 commit 含む）
- Invitation: `public/data/invitations.json`（`BETA-TEST-2026`, `BETA-F6D1-E07E`）
- CLI: `scripts/beta-admin.mjs` / `scripts/issue-invite.mjs`（`npm run beta`）
- `config/beta.json` / `public/config/beta.json` — `invitation_required: true`, `maintenance_mode: false`

### 運用
- Result Automation（`app/ops/result_automation*.py`, recovery, systemd 例）
- OPS Monitor（Pages BFF + EC2 timer 例）
- Improvement pipeline I1–I5（先行 commit）
- Infra 例: `infra/aws/systemd/`, `infra/cloudflare/env/production.env.example`

---

## Explicitly NOT enabled

| 項目 | 扱い |
|------|------|
| `WIN5_REPICK_V2_ENABLED` | **OFF**（既定 False。本番 env にも設定しない） |
| RePick V2.1 Trigger Narrowing | 設計・シミュレーションのみ。未実装 |
| Prediction V2 market features (F01) | ROI 未達のため **Archived**。Flag ON なし |
| 予想ロジックの本番切替 | **行わない** |

RePick V2 実装本体（`v2_repick_v2.py` および Optimizer hook）は研究ツリー側にコード保持。本リポジトリには設計・AB・Failure ドキュメントのみ同梱し、製品既定は identity（無変更）を維持する。

---

## Configuration (production)

`wrangler.toml` `[vars]`（非秘密デフォルト）:

- `AUTH_MODE=stub`
- `VALIDATE_CONTRACTS=soft`
- `KAOBA_PROVIDER=auto`
- `AI_ENGINE=real`

Secrets / Dashboard（本番必須・リポジトリに置かない）:

- `AI_BASE_URL`, `AI_API_KEY`
- `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`
- `OPS_MONITOR_KEY`（推奨）
- `EXPECT_ENV=production`

参照: `infra/cloudflare/env/production.env.example`  
**禁止:** `.dev.vars` のコミット、公開 Origin への AI 直結、`WIN5_REPICK_V2_ENABLED=1`

---

## Known holds

1. **Collector Go-Live HOLD** — Real KeibaNet 実接続検証が未完（RC-1 PASS と 1.0 宣言は分離）
2. **RePick V2** — AB Exit FAIL（採用停止）。Hit率改善トラックは一時停止
3. Phantom `git status` M（Windows CRLF）— 実 content diff は限定的。本リリースでは実変更 + 未追跡の安定スコープのみコミット

---

## Invite IDs shipped in seed

| invite_id | note |
|-----------|------|
| `BETA-TEST-2026` | Browser login test |
| `BETA-F6D1-E07E` | issued-on-request-2026-07-21 |

ログイン例: `https://expect-keiba.com/login?id=BETA-F6D1-E07E`（Pages 反映後）

---

## Deploy

手順は `docs/ops/deploy-procedure-2026-07-21-stable.md` を参照。
