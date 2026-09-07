# Production Reflection Audit — UI3 Contract Guard

**Audit time:** 2026-07-29 JST  
**Target host:** `https://expect-keiba.com`  
**Verified environment:** **Production only**（Staging / local `wrangler pages dev` は本監査で未使用）

---

## Verdict

| Claim | Result |
|---|---|
| UI3 `ensurePredictionBundleContract` / normalize 系が本番 BFF に載っている | **YES（振る舞い証明）** |
| Git commit `c6b3171` に UI3 ソースが含まれる | **NO** |
| 本番反映経路 | **dirty deploy**（`wrangler pages deploy … --commit-dirty=true`） |
| `2026-08-01-01-02` のブラウザ受信 ≒ サーバー応答 | **構造一致（YES）** |
| 当該レースの Guard エラー原因が「未デプロイ」か | **NO（未デプロイではない）** |

---

## 1. Deployment / Version（Production）

### Pages + Functions（同一 Cloudflare Pages デプロイ）

| Item | Value |
|---|---|
| Project | `keiba-single-ai` |
| Custom domain | `https://expect-keiba.com` |
| Active Deployment ID | `ff8b2de6-4081-4e60-8c9d-9ae44d80526f` |
| Deployment URL | `https://ff8b2de6.keiba-single-ai.pages.dev` |
| Environment | **Production** |
| Branch | `main` |
| Source commit label | `c6b3171` = `c6b317164b9eff62bce9ea015c45d342a887f4d8` |
| Commit message | `docs(baseline): record Version8.5.1 commit hash and fix registry encoding.` |
| Commit date | 2026-07-27 08:08:47 +0900 |
| Deploy age（監査時点） | ~40 minutes ago |
| Runtime | Cloudflare Pages Functions（`/api/health` → `runtime: cloudflare-pages-functions`） |

### BFF（Pages Functions 上）

| Item | Value |
|---|---|
| Probe | `GET /api/health` |
| `data.expect_env` | **`production`** |
| `data.service` | `bff` |
| `data.auth_mode` | `stub` |
| `data.status` | `degraded`（result_automation unhealthy; PI ok） |
| CF | `Server=cloudflare`, `cf-cache-status=DYNAMIC`, `CF-RAY=…-NRT` |

### Pages 静的アセット（抜粋）

本番 HTML 参照例: `prediction.js?v=11`, `contract-guard.js`, `ui-features.js?v=11`, `styles.css?v=23`

### Git との差分（重要）

- `git show c6b3171:functions/_lib/domain.js` に **`ensurePredictionBundleContract` は存在しない**
- 作業ツリーでは `functions/_lib/domain.js` が **未コミット差分**として ensure を含む
- `functions/_lib/singleToBundleMapper.js` / `functions/api/ui/` も **git 未追跡**だが本番 API は応答する  
→ **本番は commit 正本ではなく dirty デプロイ成果物を実行している**

---

## 2. UI3 が本番に存在する証明

### 方法: 振る舞いフィンガープリント（ソース漏洩ではなく出力契約）

`POST /api/ui/prediction-bundle` に **意図的に Guard 違反の core_payload** を投入:

- `race_info.venue = null`
- `race_info.race_no = "2"`（string）
- `explain.narrative` **欠落**
- `betting_recommendations.items` **欠落**
- `ai_confidence.score = "0.5"`（string）

### 本番応答（実測）

| Signal | Observed | ensure 無しだと起きにくい結果 |
|---|---|---|
| HTTP | 200 | — |
| `meta.adapter` | `singleToBundleMapper` | UI1/UI3 経路 |
| `race_info.venue` | `"unknown"` (string) | null のままなら Guard FAIL |
| `race_info.race_no` | `2` (**int**) | string のままなら Guard FAIL |
| `explain.narrative` | `""` (string) | 欠落なら Guard FAIL |
| `betting_recommendations.items` | `[]` | 欠落なら Guard FAIL |
| `ai_confidence.score` | `null` | 不正 string を落とす |
| `ensure_likely_present` | **true** | — |

Artifact: `docs/research/artifacts/prod-ui3-ensure-fingerprint.json`

**結論:** 本番 BFF に `normalizePredictionBundle` → `ensurePredictionBundleContract` 相当の正規化が **載っている**。  
「開発だけ直って本番未反映」は **この関数群については否定**できる。

---

## 3. Race `2026-08-01-01-02` — Browser vs Server

### 検証環境

| Layer | Used? |
|---|---|
| Production `expect-keiba.com` | **YES** |
| Staging | No |
| Local / wrangler dev | No |

### サーバー（PowerShell → 同一 Origin）

| Endpoint | HTTP | Shape |
|---|---|---|
| `GET /api/predictions/2026-08-01-01-02` | **202** | `ok:false`, `PREDICTION_PENDING`, `data` 無し |
| `POST /api/single/detail/2026-08-01-01-02` | **202** | 同上（SingleDetailAdapter） |
| `POST /api/ui/prediction-bundle` | **200** | Bundle あり・Guard 充足（runners=0, narrative=""） |

Artifacts:

- `pra-server-predictions-2026-08-01-01-02.json`
- `pra-server-single_detail-2026-08-01-01-02.json`
- `pra-server-ui-2026-08-01-01-02.json`

### ブラウザ（cursor-ide-browser on Production）

同一 Origin で再 fetch:

| Endpoint | HTTP | Shape match vs Server |
|---|---|---|
| predictions | 202 / PREDICTION_PENDING / data 無し | **一致** |
| single/detail | 202 / PREDICTION_PENDING / data 無し | **一致** |
| ui/prediction-bundle | 200 / schema `…/2.0` / race_no=2 / venue=unknown | **一致** |

※ raw SHA256 は `generated_at` が毎回異なるため不一致。**構造（status / error.code / fallback_reason / data 有無 / race_info）は一致。**

### 画面上の Guard メッセージ

ブラウザは error card を表示:

> PredictionBundle が契約と一致しません。  
> `schema_version` / `race_id` / `race_info`

これは **pending エンベロープ（または `{}`）を Bundle として validate したときの先頭エラー**と一致。  
サーバーが不正 Bundle を返しているのではない（predictions/single_detail は Bundle を返していない）。

---

## 4. Environment declaration（必須）

| Question | Answer |
|---|---|
| どの環境を検証したか | **Production**（`expect_env=production`, host=`expect-keiba.com`） |
| Staging を見たか | **見ていない** |
| 開発サーバーを見たか | **見ていない**（ローカルコードとの差分比較のみ） |

---

## 5. Reflection 判定

1. **UI3 ensure/normalize は本番に反映されている**（振る舞い証明）。  
2. ただし **Git commit 正本には未収録**で、**dirty Pages deploy** 依存。再現性・監査性は弱い。  
3. `2026-08-01-01-02` では本番サーバーとブラウザは **同じ pending / 同じ empty-valid UI bundle** を見ている。  
4. 当該レースの Guard 表示は **「本番未反映」では説明できない**。pending 応答のクライアント扱い側を疑うべき。

---

## Decision（監査）

| Item | Value |
|---|---|
| Action Type | Production Reflection Audit |
| Implementation Required | No（本監査の範囲外。必要なら別 Decision） |
| Deployment Required | Optional: dirty ではなく **commit 済み** で再デプロイすると監査性が上がる |
| Configuration Required | No |
| Risk | Dirty-deploy drift（ローカル未コミット ≠ remote git） |
