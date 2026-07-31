# Version8.8.1 — Dashboard Dataflow Audit

**Status:** Implemented  
**Scope:** Publish Layer + Ops Dashboard wiring（PE / CE / AI / RA / Research Logic 非変更）  
**Boundary:** Accept → RC → Deploy Note → Human Deploy（維持）  
**Production auto-apply:** false

---

## 経路（完結）

```
v8:runner（dry=false）
  → Research tick（既存）
  → finalize() → publishOpsSnapshot()
  → public/ops-data/*.json
  → Cloudflare Pages 配信
  → GET /api/ops/portal（+ live APIs）
  → /ops Dashboard
```

| モード | 状態書込 | Approval | ログ |
|--------|----------|---------|------|
| `--dry-run` | なし | **しない** | `dry-run plan=… skip_publish=1` |
| 通常 | あり | **必ず** `publishOpsSnapshot` | `publish ok week=… next=…` |

---

## Publish ファイル追跡

| ファイル | 元 | 更新タイミング | Dashboard 利用 |
|----------|----|----------------|----------------|
| `knowledge.json` | `development/knowledge/` | runner 終了時 Publish | portal → Knowledge |
| `reports.json` | `development/weekly/*/reports/` | 同上 | portal → Reports |
| `research-scheduler.json` | `development/scheduler/` | 同上 | portal + `/api/ops/research-scheduler` |
| `approval-queue.json` | `development/approvals/` | 同上（`approvals.json` 互換） | portal Approval + `/api/ops/approvals` |
| `deploy.json` | `weekly/*/sat-deploy/deploy-note.json` | 同上 | portal → Deploy |
| `portal-snapshot.json` | 上記集約 | 同上 | **主読取** |

schema（Publish）:

- `expect-v881-portal-snapshot/1.0`
- `expect-v881-*-publish/1.0`
- API portal: `expect-v881-ops-portal/1.0`

---

## Dashboard 全カード一覧

凡例: **実データ** / **No Data** / **Pending**

### System

| カード | 取得元 | API / JSON | Publish | 実データ条件 | No Data | Pending |
|--------|--------|------------|---------|--------------|---------|---------|
| Pages | `/api/health` | `status`/`runtime`/`expect_env` | — | health 取得成功 | health 失敗・欠損 | — |
| EC2 | health / snapshot.system | scalar `ec2` 等 | system（任意） | scalar あり | なし | — |
| PI | health.pi | status / latency_ms / configured | — | probe オブジェクトを整形 | なし / 未設定 | — |
| AI | health | `ai` or `ai_proxy_configured` + RA 要約 | — | 上記あり | なし | — |
| ResultAutomation | live | `/api/ops/result-automation` → `run.status` | — | run/status あり（例 FAILED） | API 失敗・欠損 | — |
| Research Scheduler | Publish | portal-snapshot / research-scheduler | current_phase | phase あり | null | — |

### Production

| カード | 取得元 | 実データ | No Data | Pending |
|--------|--------|----------|---------|---------|
| Prediction〜Realtime | `/api/ops/v71-metrics` | metrics の status 等 | 未取得・キーなし | — |
| Maintenance | ops-mode | `PUBLIC` / `CLOSED`（実効モード） | モード不明 | — |

### Research

| カード | Publish キー | 実データ | No Data |
|--------|--------------|----------|---------|
| Current Week | `research.week_id` | week_id | null |
| Current Phase | `research.current_phase` | phase 文字列 | null |
| Next Run | `research.next_run` | ISO `…T03:00:00+09:00` | null（固定「毎日…」禁止） |
| Recovery | `research.recovery` / `recovery_active` | `active`/`idle`（boolean 由来） | 実値なし |
| Decision | `research.decision` | 決定値 | null |

### Knowledge / Deploy / Reports / Approval

| セクション | カード | Publish | 実データ | No Data | Pending |
|------------|--------|---------|----------|---------|---------|
| Knowledge | Score / Accepted / Rejected / Governance | knowledge.* | 数値・文字列あり | null | — |
| Deploy | Queue / Accept候補 / deploy-note | deploy.* | note あり | null | — |
| Reports | Weekly Report | reports.weekly_report | week_id 等 | なし | — |
| Reports | Baseline / Boundary | reports.* | レポート値 | レポート自体なし | レポートあり・フィールド未記入時 `Pending` |
| Reports | Incident | incident_report | あり | なし | — |
| Approval | Pending/Approved/Rejected/Timeout | approval-queue + `/api/ops/approvals` | 件数 | キュー未 publish | — |
| Approval | 一覧 / expires_at / 残り日数 / Approve / Reject | Queue items | item フィールド | pending なし → No Data | — |

---

## 表示ポリシー（完了条件）

Dashboard に出してよい値:

1. **実データ**（Publish / health / live API）
2. **No Data**（欠損・取得失敗）
3. **Pending**（成果物はあるが当該フィールド未確定）

禁止: 固定 `OK` / 固定 `毎日 03:00 JST` / ダミー / `String(object)` → `[object Object]`

---

## 修正内容（本リリース）

1. **Runner:** dry-run は plan のみ（状態・Publish なし）。通常は必ず `publishOpsSnapshot` + `publish ok` ログ
2. **portal.js:** Pages 固定 OK 撤去、PI `formatProbe`、Production 初期 No Data、Approval 集計カード、stub 除去
3. **ops-portal-v87.js:** object 表示禁止、Approval Queue 全件＋件数カード、残り期限 No Data
4. **approvals.js:** `approval-queue.json` 優先読取（HTML フォールバック拒否）
5. **_headers:** `/ops-data/*` JSON + no-cache
6. **Pages:** `public/ops-data` v881 成果物をデプロイして本番反映

---

## 運用メモ

- EC2: `npm run v8:runner`（timer）が毎日 Publish する
- 手動: `npm run v8:publish`
- スモーク: `npm run v8:smoke881`
