# Permanent Prediction Recovery Design

**Phase:** PROD-PREDICTION-PERMANENT-RECOVERY-01  
**Status:** DESIGN ONLY — Owner gate before any implementation or Production change  
**Date:** 2026-08-15  
**Production changed:** NO  

Related:

- Integrity audit: Single/Win5 は同一 `expect-ai`。公開予測 authority は `:8000`
- ID cutover branch: `cursor/race-id-contract-22d3`（未 Production）
- Deploy sketch: `infra/aws/github-actions/README.md`（workflow 未実装）

---

## 0. Principles (absolute)

1. Catalog ID と Core/Feature key は別 namespace。文字列の形で推測しない。
2. 物理 identity の正本は `numeric_race_id`（JRA 12桁）。
3. 公開予測 authority は `expect-ai :8000` のみ。
4. Runtime tree は単一。systemd 例と live を一致させる。
5. Production dirty-only ロジックを禁止。動いている挙動は git に正式化する。
6. Normal / Maiden は `RaceTypeRouter` のコード契約。adapter の文字列推測禁止。
7. mock / dummy Bundle を user-visible 予想として返さない。
8. Owner Windows PEM に deploy を依存させない。
9. Feature readiness は予測リクエスト前に観測可能。
10. public / origin / runtime provenance を response から確認できる。

研究ロジックの再学習・Repick ON・RESTORED_V2 スコア変更はしない。  
配線・契約・観測・deploy の恒久化のみ。

---

## Current Architecture Problems

| # | 問題 | 実コード / 証拠 |
|---|---|---|
| P-ID | `YYYY-MM-DD-NN-NN` が Catalog（label_no）と Core（venue 桁）で同形 | `RaceResolver._parse` dotted 枝。8/16 `03-10` が Catalog 未hit 時に Core fallback |
| P-MAP | venue map が二重 | `catalog_index.JRA_VENUE_CODE_TO_JA`（03=福島）vs `race_resolver._VENUE_CODE_TO_JA`（03=函館） |
| P-FEATKEY | Feature CSV の `race_id` は **Catalog/Win5 ID** | `pi_keibanet/race_refresh.py` `make_win5_race_id` → `race_id: win5_id`。FeatureLoader は渡された key で exact match。JRA-Core に変換すると **当たっていた行を外す** |
| P-TREE | APP 正本が分裂 | live health `db=/home/ubuntu/KEIBA-Single-AI/...`。systemd 例 `WorkingDirectory=/opt/expect-ai/current` |
| P-OVERLAY | Single が不完全 overlay + platform 残存 | overlay 12 files。`ai_platform.single.api` / `PRODUCT_VERSION` / `demo_probability_*` / Ranker / World は overlay 外 |
| P-DIRTY | RESTORED_V2 が git 外 | 公開 control は `decision_authority=RESTORED_V2` / `model_version=restored-v2-baseline/ed369a89`。repo 0件 |
| P-MAIDEN | CURRENT_PATH 不在 | repo 0件。8/16 新馬も `race_type=NORMAL` + mock |
| P-MOCK | 未解決を阪神11R dummy で 200 | `RealAiPredictionSource._mock_one` → `bundle-20260719_hanshin_11`。origin 18s+、UI 14s timeout |
| P-READY | coverage が予測 list を回す | `coverage.compute_coverage` → `prediction_adapter.list_with_meta`。8/16 `race_total=0`。timer active ≠ feature generated |
| P-AUTH | BFF が PI primary → Python failover | `functions/_lib/adapters/predictionAdapter.js` `adaptPredictionGet`。LIVE は同一 hostname のため PI predictions は :8000 に落ち、`prediction_available` 無し → Python |
| P-TUNNEL | repo と LIVE 不一致 | `infra/cloudflare/tunnel-ai-ingress.json` `/v1/predictions`→8081。LIVE は 8000 |
| P-TO | timeout 階層破綻 | UI `race.html` 14000 / BFF python get 10000 / `aiProxy` default 12000 / origin 18–47s |
| P-DEPLOY | Cloud Agent SSH 不可。Owner PEM のみ | `.github/workflows` は contract test のみ。`deploy.yml` 無し |

---

## Target Architecture

```
Browser
  → Pages BFF
       /api/races*        → PI_BASE_URL  → :8081  catalog only
       /api/predictions*  → AI_BASE_URL  → :8000  expect-ai only
  → Tunnel (LIVE契約)
       /v1/races*         → 127.0.0.1:8081
       /v1/predictions*   → 127.0.0.1:8000
       /v1/conversation*  → 127.0.0.1:8000

expect-ai :8000  (WIN5_AI HTTP)
  RaceIdentityResolver     ← 唯一の ID 変換
  FeatureReadiness         ← 日付/レース観測。未準備は即時
  RaceTypeRouter           ← NORMAL | MAIDEN（Catalog metadata）
  PredictionAdapter
       NORMAL  → RESTORED_V2 (git 正式) → Single/Core
       MAIDEN  → CURRENT_PATH (存在確認後に配線。未配置なら fail-closed)
  PredictionBundle 2.0     ← 成功時のみ user-visible horses
  Unavailable envelope     ← 失敗時。dummy 禁止

AI_PLATFORM_ROOT           (SINGLE_AI artifact)
  ai_platform.single.api
  CorePipeline / ModelRegistry / FeatureLoader
  model pin (SHA256)

PI :8081
  catalog + race_refresh のみ。公開予測 authority にしない
```

---

## ID Namespace Contract

### 型（文字列をそのまま downstream に流さない）

実装先（P1）:

- **NEW** `services/win5-ai/app/data/race_refs.py`
  - `CatalogRaceRef(date, meeting_label, race_no)` → `as_catalog_id()`
  - `CoreRaceRef(date, jra_venue_code, race_no)` → `as_core_id()`  ※JRA 公式コード。Feature key ではない
  - `VenueQualifiedRaceRef(date, venue_name, race_no)`
  - `NumericRaceRef(numeric_race_id)`  ※物理正本
  - `FeatureLookupRef(key, source)`  ※CSV/DB の `race_id` 列
  - `ResolvedRaceIdentity`（既存 `RaceIdentity` を拡張 / 置換）

既存 `RaceIdentity` は残し、内部を typed ref に置き換える。公開文字列は `as_*()` だけ。

### 変換責任は1箇所

`RaceIdentityResolver` = 現行 `RaceResolver` + `CatalogIndex` の統合正面。

| 入力 | 判定順 | 禁止 |
|---|---|---|
| `YYYY-MM-DD-NN-NN` | 1) Catalog exact 2) Numeric 経由の逆引き 3) **明示** `id_namespace=core` のときだけ Core | NN を venue と読む |
| venue-qualified / slug | date+venue+race で Catalog lookup | 独自 map |
| 12桁 | `NumericRaceRef` → Catalog 行 | 桁切り venue 推測を Feature key にする |

Catalog → 物理/Core:

1. `numeric_race_id[4:6]` = JRA venue（`catalog_index.JRA_VENUE_CODE_TO_JA` のみ）
2. 無ければ Catalog `course` 名
3. meeting label から venue を決める場合は **その日の PI catalog を lookup**（固定会場順表で決めない）

### Feature lookup key（今回の最重要訂正）

`pi_keibanet.race_refresh` は Feature 行の `race_id` に **Win5 Catalog ID** を書く。  
control `2026-07-25-01-05` の `feature_lookup_key` もその文字列。

```
feature_lookup_key :=
  1. Feature CSV/DB に numeric_race_id で当たる行の race_id
  2. 無ければ Catalog ID（PI refresh 契約）
  3. レガシー日のみ明示 pin（manifest）
```

**禁止:** Catalog→JRA-Core 変換結果を無条件に FeatureLoader に渡す。  
8/16 札幌10R:

| 空間 | 値 |
|---|---|
| Catalog | `2026-08-16-03-10` |
| Numeric | `202601010810` |
| JRA-Core | `2026-08-16-01-10` |
| Feature key（PI 生成後） | `2026-08-16-03-10` |

JRA-Core は説明・衝突回避用。推論入力 key は `FeatureLookupRef`。

`_VENUE_CODE_TO_JA`（03=函館）は **Feature レガシー日の pin 以外で使わない**。削除は P1 ではしない（7/19 福島キー汚染防止）。呼び出しを Resolver 1箇所に閉じる。

### 単一 authority

- Catalog SoT: PI `/v1/races?date=` + `numeric_race_id` + venue + race_no
- win5 `CatalogIndex` は PI を読み、fixture は PI 不通時の pin
- BFF `functions/_lib/raceIdResolve.js` は **Catalog 行の exact match のみ**。Core 変換を持たない
- frontend は ID を作らない。PI catalog の `race_id` をそのまま予測に渡す

### P1 exact files

| 操作 | path | 関数 |
|---|---|---|
| NEW | `app/data/race_refs.py` | 4 ref + `ResolvedRaceIdentity` |
| EDIT | `app/data/catalog_index.py` | `core_race_id_from_catalog`, `CatalogIndex.lookup_*` — JRA map のみ |
| EDIT | `app/data/race_resolver.py` | `_parse` dotted: Catalog first。Core fallback は `id_namespace` 明示時のみ。`_VENUE_CODE_TO_JA` を Feature key に使わない |
| EDIT | `app/engine/adapters/single_prediction_mapper.py` | `diagnose_inference`: FeatureLoader に `feature_lookup_key` |
| EDIT | `pi_keibanet/race_refresh.py` | Feature CSV に `numeric_race_id` 列を必須化。`race_id` は Catalog のまま（ロジック非変更） |
| EDIT | overlay `feature_loader.py` | lookup: numeric → catalog → 明示 key。**スコア計算は不変** |
| TEST | `tests/ops/test_race_namespace_contract.py` | 下記 |
| KEEP | `tests/ops/test_catalog_core_bridge_2026_08_16.py` | 36R + 衝突 |

P1 tests（日付非依存）:

- 3場 / 2場 / 1場
- meeting order 変化（label_no が会場固定でない）
- venue code 衝突（label `03` ≠ JRA `03`）
- canonical string collision（Catalog `...-01-10` ≠ JRA-Core `...-01-10`）
- race 1–12
- 複数日（fixture 2日以上）
- Feature key ≠ JRA-Core でも load できる
- レガシー `2026-07-19-04-11` 福島 feature key 非破壊

---

## Single AI Runtime Contract

Single は独立 systemd ではない。`expect-ai` が import する **完全 artifact**。

### 必要モジュール（manifest 必須）

| 役割 | モジュール | 今 overlay? |
|---|---|---|
| API | `ai_platform.single.api.get_prediction` | **NO** |
| predict | `ai_platform.single.prediction.predict` | YES |
| models | `ai_platform.single.models` + `PRODUCT_VERSION` | 部分（`PRODUCT_VERSION` 無し） |
| Core | `CorePipeline.evaluate` | YES |
| Facade | `ai_platform.core.facade` | YES |
| Features | `FeatureLoader` / `FeatureGenerator` | YES（`demo_probability_*` 依存は外） |
| Score | `ModelRegistry` / `Scorer` | YES（demo 依存は外） |
| Rank/World | `ai_platform.core.ranking` / `world` | **NO** |
| Bets | `single.bet_builder` / `bet_strategy` | **NO** |

P2 で `services/win5-ai/platform/single-ai.manifest.json` を作り、  
`AI_PLATFORM_ROOT` 上の実ファイル SHA256 と照合。欠けたら `SINGLE_AI_RUNTIME_READY=false`。

overlay コピー（`app/core/platform_overlay.py`）は残してよいが、**欠けたファイルを platform 残存に頼って黙って成功させない**。

### health

`GET /health` に追加（秘密なし）:

```
app_root, platform_root, data_root, git_sha, build_id,
SINGLE_AI_RUNTIME_READY, missing_modules[],
model_path, model_sha256, model_pin
```

実装: **NEW** `app/ops/runtime_manifest.py` `build_health_runtime()`  
配線: `app/main.py` `/health`

### 正本 tree

| 名前 | 恒久 path | 初期移行 |
|---|---|---|
| APP_ROOT | `/opt/expect-ai/current` | live が home clone なら **symlink** `current → /home/ubuntu/KEIBA-Single-AI`。コード移動は別 Owner gate |
| PLATFORM_ROOT | `/opt/expect-ai/platform` | 現行 runbook を正式化 |
| DATA_ROOT | `/var/lib/expect-ai` または `PLATFORM_ROOT/data` | 初回は **動かさない**。`EXPECT_AI_DB_PATH` / `PI_DATA_ROOT` を明示 |

systemd **正式ファイル**（example を廃止）:

- **REPLACE** `infra/aws/systemd/expect-ai.service.example` → `infra/aws/systemd/expect-ai.service`
- 必須 Environment:
  - `WorkingDirectory=${APP_ROOT}/services/win5-ai` または APP_ROOT
  - `PYTHONPATH=${APP_ROOT}/services/win5-ai:${PLATFORM_ROOT}`
  - `AI_PLATFORM_ROOT=/opt/expect-ai/platform`
  - `EXPECT_AI_DB_PATH` 明示
  - `AI_ENGINE=real`
  - `CORE_MODEL_PATH` 明示
  - `AI_PORT=8000`

PI unit も同じ PLATFORM/DATA を書く（既に近い）。

---

## Win5 AI Runtime Contract

| 項目 | 契約 |
|---|---|
| source | `${APP_ROOT}/services/win5-ai` |
| entry | `run.py` → `app.main` |
| service | `expect-ai.service` |
| port | **8000** |
| 責務 | HTTP、Resolver、Router、Adapter、Bundle、Conversation、health/ops |
| 推論 | Single/Core を呼ぶだけ |
| Bundle owner | `prediction_adapter` + `single_prediction_mapper.prediction_response_to_bundle` |
| FeatureLoader owner | `ai_platform.core.features`。DB provider は `app.core` |

公開予測に PI `:8081` `get_prediction` を使わない。

---

## RESTORED_V2 Formalization

### 現状

git に記号なし。Production dirty adapter が成功時に stamp。  
control 固定（変更禁止）:

| 項目 | 値 |
|---|---|
| id | `2026-07-25-01-05` |
| top1 | キシダンチョウ |
| authority | RESTORED_V2 |
| engine_source | real_ai |
| model | `restored-v2-baseline/ed369a89` |
| venue | 新潟 5R |

### やること（ロジック変更禁止）

1. Owner READ（実装前必須）:
   - `systemctl show expect-ai -p WorkingDirectory,ExecStart,Environment,MainPID`
   - `/proc/$PID/cwd` `/proc/$PID/environ`
   - dirty `prediction_adapter.py` 全文 + sha256
   - runtime が読む model ファイル path + sha256
2. 差分を **NEW** `app/engine/authority/restored_v2.py` に抽出
   - `apply_restored_v2_authority(bundle, diag) -> bundle`
   - `model_version` pin
   - `decision_authority`, `fallback_state=restored_v2`
   - 公開で観測済みの meta キーのみ（`race_type` は Router へ移管）
3. git `prediction_adapter.py` から呼ぶ。dirty 上書きは **抽出後の同一挙動テストが通ってから**
4. model pin: `services/win5-ai/platform/models/restored-v2.manifest.json`

```
{ "id": "restored-v2-baseline", "pin": "ed369a89", "sha256": "<prod read>", "path": "<prod read>" }
```

5. Golden: **NEW** `tests/ops/test_restored_v2_control_2026_07_25.py`  
   fixture: 公開 control の Bundle スナップショット（horses / authority / versions）

NORMAL → RESTORED_V2 は Router 契約。adapter 内 if 文字列禁止。

**P3 実装は Production READ なしでは BLOCK。** スケルトンと golden fixture（公開 JSON）は git に置ける。

---

## Maiden Routing Contract

### Router

**NEW** `app/engine/routing/race_type_router.py`

```
classify(catalog_row) -> RaceType.NORMAL | RaceType.MAIDEN
```

入力: Catalog metadata のみ（`race_name` / `class_label` / PI `race_name`）。  
adapter の ID 推測禁止。

Maiden（日本語 Catalog 契約）:

- `新馬`
- `未勝利`
- 明示 `maiden`（あれば）

それ以外（1勝 / 2勝 / OP / 重賞 / 特別一般）= NORMAL。

出力後:

| type | engine |
|---|---|
| NORMAL | RESTORED_V2 |
| MAIDEN | CURRENT_PATH |

### CURRENT_PATH

repo / 公開 path に **存在しない**。P4 手順:

1. Owner READ: platform / win5 を `CURRENT_PATH` / maiden model で検索
2. 見つかれば dirty と同様に git 正式化（ロジック非変更）
3. **無い場合:** fail-closed  
   `prediction_available=false`, `reason=maiden_runtime_missing`  
   **RESTORED_V2 に落とさない**（contamination 0）

仮の Maiden モデルを新造しない。

### tests

**NEW** `tests/ops/test_race_type_router.py`

- 2歳未勝利 / 3歳未勝利 / 新馬 → MAIDEN
- 1勝 / OP / 重賞 → NORMAL
- NORMAL→MAIDEN = 0
- MAIDEN→RESTORED_V2 = 0（CURRENT_PATH 未配置でも）

8/16 札幌5R `2026-08-16-03-05` `race_name=2歳新馬` を fixture に含める。

---

## Mock Policy

Production: `DISABLED_FOR_USER_VISIBLE_PREDICTION`

| 条件 | 返さないもの | 返すもの |
|---|---|---|
| race 未解決 | 阪神11R dummy horses | `prediction_available=false`, `reason=race_not_resolved` |
| feature なし | dummy | `reason=feature_not_ready` |
| input なし | dummy | `reason=input_not_ready` |
| 推論エラー | dummy | `reason=inference_error` |
| maiden runtime なし | RESTORED_V2 | `reason=maiden_runtime_missing` |

HTTP: **200 + envelope**（Client/BFF が 4xx で真っ白になるのを避ける）。  
`data` は Bundle ではなく readiness オブジェクト。horses 配列を載せない。

```
{ "ok": true,
  "data": { "prediction_available": false, "reason": "...", "race_id": "..." },
  "meta": { "adapter": "PredictionAdapter", "engine_source": "unavailable", ... } }
```

成功時のみ `single-prediction-bundle/2.0`。

| 操作 | path |
|---|---|
| EDIT | `prediction_adapter.py` `_mock_one` を prod で呼ばない。`AI_ALLOW_USER_VISIBLE_MOCK=0` default |
| EDIT | `app/main.py` get が unavailable を 200 envelope で返す |
| EDIT | `functions/_lib/adapters/predictionAdapter.js` dummy 投影を Production で禁止 |
| EDIT | `public/assets/api/prediction.js` / `public/race.html` unavailable UI |
| KEEP | mocks は `tests/` と `AI_ENGINE=mock` のみ |

`coverage.py` は list 予測を回して mock 率を数えない。FeatureReadiness を見る。

---

## Feature Readiness Contract

**NEW** `app/data/feature_readiness.py` `FeatureReadinessService`

日付単位 + レース単位:

```
catalog_ready, entries_ready, odds_ready,
feature_rows, race_count, feature_ready,
generated_at, source,
last_success_at, last_generated_date, failed_stage
```

予測 get:

```
resolve identity
 → FeatureReadiness.for_race(feature_lookup_key | numeric)
 → not ready: 即時 unavailable（目標 < 2s、dummy 生成なし）
 → ready: infer
```

`classify_feature_availability` の **load 試行は残してよいが、先に path/index で判定**する。  
巨大 CSV 全読 + mock 組立（18–47s）を禁止。

### Day-of automation

既存:

- `expect-pi-race-refresh.timer` 15min、08–20 JST
- `scripts/prod_race_refresh.py` → `PI_DATA_ROOT/.../demo_daily_outputs/<date>/demo_runners_pace_market_features.csv`

契約: **timer active ≠ feature generated**

`/health` または **NEW** `/v1/ops/feature-readiness?date=`:

- refresh `last_success_at` / `features_generated` / `error_count`（`race_refresh` report JSON）
- `catalog_count` vs `feature_rows`
- 8/15・8/16 型: catalog>0 && feature_rows==0 → `CATALOG_WITHOUT_FEATURES`

手動 Feature 生成で隠さない。P5 は観測と fail-fast。ETL 中身の再研究はしない。

win5 `EtlScheduler` と PI refresh の二重生成は P5 で **どちらが Production Feature SoT か明記**する。  
live control は `daily_csv` = PI/platform daily が SoT。win5 ETL は補助。SoT をコードと health に書く。

---

## Public Authority Contract

| path | process | port |
|---|---|---|
| `/v1/predictions*` | expect-ai | **8000** |
| `/v1/conversation*` | expect-ai | **8000** |
| `/v1/races/resolve` | expect-ai Resolver | **8000** |
| `/v1/races` `/v1/races/{id}` | PI catalog | **8081** |
| PI `/v1/predictions` | 内部/legacy。Tunnel に出さない | 8081 |

`PUBLIC_PREDICTION_RUNTIME = expect-ai:8000`

---

## BFF / Tunnel Contract

### BFF

`adaptPredictionGet` / `adaptPredictionList`:

- Prediction: `AI_BASE_URL` only。PI predictions を見ない
- Catalog: `PI_BASE_URL` only
- `pi_unavailable_ai_failover` 削除
- `piPredictionMapper` / PI envelope は legacy。P6 で未使用化
- list の catalog 投影は **予測ではない**。ホーム用なら `/api/races` を使え。予測 list に dummy Bundle を混ぜない

timeout（P6。UI だけ 60s にしない）:

| 層 | Feature 未準備 | Feature 準備済み推論 |
|---|---|---|
| origin | fail-fast < 2s | budget 20s（cold 実測後に pin） |
| BFF `aiFetch` predictions | 8s | 25s |
| UI `race.html` | 10s | 30s |

階層: **UI > BFF > origin**。今は UI 14 < BFF 10 < origin 18 で破綻。

exact files:

- `functions/_lib/adapters/predictionAdapter.js`
- `functions/_lib/aiProxy.js`（default 12000 を予測と分離）
- `public/race.html`（14000）
- `public/assets/api/prediction.js`（18000 default）

### Tunnel

repo を LIVE に合わせる（**適用は別 Production gate**）:

`infra/cloudflare/tunnel-ai-ingress.json`

```
/v1/races/resolve → 8000
/v1/races         → 8081
/v1/predictions   → 8000    # 今 repo は 8081。LIVE は 8000
default           → 8000
```

この PR/Phase では JSON を直すだけ。CF API PUT は Owner gate。

---

## Deployment Pipeline Design

Owner PEM 依存を終了する。Cloud Agent に PEM を持たせない。

### 選定: GitHub Actions OIDC → AWS SSM

既存スケッチ: `infra/aws/github-actions/README.md`

| 方式 | 採用 | 理由 |
|---|---|---|
| GHA + SSH + PEM in GitHub secret | 否 | PEM が secret に残る。今回の依存の焼き直し |
| **GHA OIDC → IAM → SSM Run Command** | **採用** | インスタンス SG :22 を開けない。Agent に鍵不要 |
| SSM のみ手動 | 補助 | Owner 緊急 rollback |

### 流れ

```
approved tag / workflow_dispatch(git_sha)
  → GHA: checkout, test, build manifest
  → S3: expect-ai/releases/<sha>/artifact.tgz + production_manifest.json
  → SSM: 
       predeploy hash
       backup current + db + adapter + models
       extract /opt/expect-ai/releases/<sha>
       flip current symlink
       overlay verify (manifest)
       systemctl restart expect-ai   # のみ。PI/tunnel/Pages は別 job
       health + SINGLE_AI_RUNTIME_READY
       golden: 2026-07-25-01-05 RESTORED_V2 キシダンチョウ
       失敗 → symlink 戻して restart
```

### exact files（P7）

| NEW | 役割 |
|---|---|
| `.github/workflows/deploy-expect-ai.yml` | workflow_dispatch + tag |
| `scripts/ops/prod-deploy-ssm.sh` | instance 側（SSM が実行） |
| `scripts/ops/prod-rollback-ssm.sh` | 直前 release へ |
| `infra/aws/iam/gha-deploy-role.md` | OIDC trust / SSM / S3 最小権限 |
| `services/win5-ai/production_manifest.json` | 下記 |

Secrets: AWS は OIDC。`AI_API_KEY` / Tunnel token は **SSM Parameter**。GHA に置かない。

Pages/BFF は既存 Pages 自動 deploy。予測 origin と **同じ日に黙って混ぜない**。BFF 契約変更は別 workflow。

---

## Runtime Manifest Design

**NEW** `services/win5-ai/production_manifest.json`（git）  
runtime は起動時に実ファイルと照合し `/health` と **NEW** `/v1/ops/runtime-manifest` で返す。

```json
{
  "app_version": "single-ai/0.1.0-m2",
  "git_sha": "<ci>",
  "build_id": "<ci>",
  "app_root": "/opt/expect-ai/current",
  "platform_root": "/opt/expect-ai/platform",
  "files": [
    { "path": "services/win5-ai/app/engine/adapters/prediction_adapter.py", "sha256": "..." },
    { "path": "services/win5-ai/app/data/race_resolver.py", "sha256": "..." },
    { "path": "services/win5-ai/app/data/catalog_index.py", "sha256": "..." }
  ],
  "models": [
    { "id": "restored-v2-baseline", "pin": "ed369a89", "sha256": "<prod>", "path": "<prod>" }
  ],
  "platform_modules": [
    "ai_platform.single.api",
    "ai_platform.single.prediction",
    "ai_platform.core.candidate_evaluation",
    "ai_platform.core.scoring.model_registry",
    "ai_platform.core.features.feature_loader"
  ],
  "routing_contract": {
    "NORMAL": "RESTORED_V2",
    "MAIDEN": "CURRENT_PATH"
  },
  "public_prediction": { "service": "expect-ai", "port": 8000 }
}
```

「どのコードが本番か分からない」を終了する。

---

## Migration Phases

一度に Production へ入れない。各 Phase: design（本資料）→ tests → Owner gate → deploy → regression。

| Phase | 内容 | 実装可能? | Production 依存 |
|---|---|---|---|
| **P1** | ID namespace + FeatureLookupRef | YES（git） | なし。deploy は Owner/CI |
| **P2** | runtime/source/model manifest + health | YES（path は live を読む） | health 追加は低リスク。tree 移動は別 gate |
| **P3** | RESTORED_V2 を git へ | スケルトン YES。本文 **READ 後** | dirty adapter + model sha |
| **P4** | RaceTypeRouter + CURRENT_PATH | Router YES。engine は READ 後 or fail-closed | CURRENT_PATH 探索 |
| **P5** | mock policy + FeatureReadiness | YES | 公開契約変更。Client 同時 |
| **P6** | timeout / BFF / tunnel JSON | YES | Tunnel **適用**は別 gate |
| **P7** | GHA+SSM deploy | YES（IAM は Owner） | AWS account / instance id |

推奨順を守る。P5 を P1 より先に入れると 8/16 は即 unavailable になるが、dummy+timeout より正しい。  
**P1 なしで Feature を JRA-Core key で探すと control を壊しうる。** P1 の FeatureLookupRef が先。

### Phase ごとの Owner gate チェック

P1: 36R map + control キシダンチョウ + レガシー福島 key  
P2: health に app_root/git_sha。`SINGLE_AI_RUNTIME_READY` が実状態と一致  
P3: control 完全一致（authority / top1 / model pin）  
P4: 新馬が RESTORED_V2 に入らない  
P5: dummy horses = 0。未準備 < 2s  
P6: BFF が AI only。tunnel JSON=LIVE。timeout UI>BFF>origin  
P7: PEM 無しで tag → deploy → golden → rollback ドライラン

---

## Rollback Strategy

- 単位: `expect-ai` のみ（既定）。PI / tunnel / Pages は同じ rollback に混ぜない
- 手段: `/opt/expect-ai/releases/<prev>` へ `current` を戻し restart
- 保持: 直前 5 release + dirty adapter 初回バックアップ（P3 前に必須）
- 判定失敗: control top1 / authority 不一致、health 非 ok、READY フラグ偽陽性
- P5 envelope 変更を戻すときは BFF/UI を **同じ rollback セット**にする
- Tunnel 適用後の切り戻しは CF 前設定 JSON を S3 に保存

---

## Risks

| リスク | 影響 | 緩和 |
|---|---|---|
| Catalog→JRA-Core を Feature key にする | control / 8/16 とも miss | FeatureLookupRef。P1 必須 |
| dirty adapter 未 READ で git を上書き | RESTORED_V2 消失 | P3 前バックアップ + golden |
| CURRENT_PATH を新造 | 研究再開。contamination | fail-closed。新モデル禁止 |
| mock 廃止で UI 真っ白 | 可用性誤解 | unavailable envelope + UI |
| `/opt` へ突然移動 | 起動不能 | まず symlink。移動は別 gate |
| repo tunnel を LIVE に適用し predictions→8081 | 公開予測が PI envelope に | JSON を 8000 に直してから適用 |
| timeout だけ延長 | dummy 待ちが長くなる | P5 fail-fast が先 |
| GHA に PEM | 依存が残る | SSM + OIDC のみ |
| 全 Phase 一括 deploy | 切り分け不能 | Phase 単位 |

---

## Exact impact map (existing)

触る（Phase 別）。予測スコア関数は触らない。

```
P1  app/data/race_refs.py                          NEW
    app/data/catalog_index.py                      EDIT
    app/data/race_resolver.py                      EDIT
    app/engine/adapters/single_prediction_mapper.py EDIT
    platform/.../feature_loader.py                 EDIT lookup only
    pi_keibanet/race_refresh.py                    EDIT columns only
    tests/ops/test_race_namespace_contract.py      NEW

P2  app/ops/runtime_manifest.py                    NEW
    app/main.py /health                            EDIT
    infra/aws/systemd/expect-ai.service            NEW (example 置換)
    platform/single-ai.manifest.json               NEW

P3  app/engine/authority/restored_v2.py            NEW (after READ)
    app/engine/adapters/prediction_adapter.py      EDIT call site
    platform/models/restored-v2.manifest.json      NEW
    tests/ops/test_restored_v2_control_*.py        NEW

P4  app/engine/routing/race_type_router.py         NEW
    prediction_adapter.py                          EDIT route only
    tests/ops/test_race_type_router.py             NEW

P5  prediction_adapter.py                          EDIT no user mock
    app/data/feature_readiness.py                  NEW
    app/data/coverage.py                           EDIT stop list-infer
    app/main.py                                    EDIT envelope
    functions/_lib/adapters/predictionAdapter.js   EDIT
    public/race.html, public/assets/api/prediction.js EDIT

P6  predictionAdapter.js / aiProxy.js / race.html  EDIT
    infra/cloudflare/tunnel-ai-ingress.json        EDIT (apply later)

P7  .github/workflows/deploy-expect-ai.yml         NEW
    scripts/ops/prod-deploy-ssm.sh                 NEW
    scripts/ops/prod-rollback-ssm.sh               NEW
    production_manifest.json                       NEW
```

禁止（全 Phase）:

- RESTORED_V2 / Core の学習・温度・特徴式変更
- `WIN5_REPICK_V2_*` ON
- 手動 Feature で 8/16 を隠す
- Tunnel 実適用を設計 PR に含める
- Cloud Agent からの Production deploy

---

## Decision

**PERMANENT_RECOVERY_DESIGN_READY**

設計と影響範囲は確定。実装は Owner gate 後、Phase 順。

実装ブロック（設計は READY）:

- P3 本文: Production dirty adapter / model sha の READ
- P4 engine: CURRENT_PATH の有無。無ければ fail-closed で契約は成立
- P7 IAM: AWS account / instance / OIDC は Owner 設定

`PRODUCTION_CHANGED = NO`  
`IMPLEMENTATION_STARTED = NO`
