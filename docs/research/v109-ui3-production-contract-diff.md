# UI3 Production Contract Diff（実レスポンス証拠）

**Probed at:** 2026-07-29 JST  
**Sample race_id:** `2026-07-26-01-11`  
**Guard:** `ExpectContractGuard.validatePredictionBundle`（`public/assets/api/contract-guard.js`）  
**Artifacts:** `docs/research/artifacts/prod-*-2026-07-26-01-11.json`  
**Scan:** `docs/research/artifacts/prod-guard-scan-2026-07-26.json`（36/36 PASS）

---

## 1. Guard 必須フィールド（正本）

| Field | Rule |
|---|---|
| `schema_version` | `single-prediction-bundle/2.0` |
| `race_id` | non-empty string |
| `race_info` | object |
| `race_info.venue` | string |
| `race_info.date` | string |
| `race_info.race_no` | **number** |
| `evaluation.runners` | array |
| `ai_confidence.score` | present（number \| null） |
| `explain.narrative` | **string** |
| `betting_recommendations.items` | array |

---

## 2. 本番 HTTP / JSON（実測）

### POST `/api/single/detail/2026-07-26-01-11`

| Item | Value |
|---|---|
| HTTP Status | **200** |
| Envelope `ok` | `true` |
| `meta.contract` | `PredictionBundle` |
| `meta.contract_validated` | `true` |
| `meta.contract_ok` | **true** |
| `meta.fallback_reason` | `CORE_PAYLOAD_REQUIRED` |
| `meta.source` | `pi-keibanet-api` |
| `data.schema_version` | `single-prediction-bundle/2.0` |
| `data.race_id` | `2026-07-26-01-11` |
| `data.race_info.venue` | `"新潟"` (string) |
| `data.race_info.date` | `"2026-07-26"` (string) |
| `data.race_info.race_no` | `11` (**number**) |
| `explain.narrative` | string（非空） |
| `evaluation.runners` | array length **15** |
| `ai_confidence.score` | number ≈ `0.497` |
| `betting_recommendations.items` | array length **0** |
| Client Guard | **PASS** (`errors: []`) |

**normalize / ensure:** meta `contract_validated=true` + `contract_ok=true` は BFF 側 `normalizePredictionBundle` → `ensurePredictionBundleContract` 通過の証拠。

### POST `/api/ui/prediction-bundle`（body: `{ "race_id": "2026-07-26-01-11" }`）

| Item | Value |
|---|---|
| HTTP Status | **200** |
| Envelope `ok` | `true` |
| `meta.source` | `bff-local` |
| `meta.adapter` | `singleToBundleMapper` |
| `data.schema_version` | `single-prediction-bundle/2.0` |
| `data.race_id` | `2026-07-26-01-11` |
| `data.race_info.venue` | `"unknown"` (string) ※core_payload 無しの最小経路 |
| `data.race_info.date` | `"2026-07-26"` (string) |
| `data.race_info.race_no` | `11` (**number**) |
| `explain.narrative` | `""` (string) |
| `evaluation.runners` | array length **0** |
| `ai_confidence.score` | `null`（キー存在） |
| `betting_recommendations.items` | array `[]` |
| Client Guard | **PASS** (`errors: []`) |

※ `core_payload` / predictions 由来の rich body を渡した場合は venue=`新潟`・runners>0 でも Guard PASS（先行 probe `cg-ui.json`）。

### GET `/api/predictions/2026-07-26-01-11`（Flag OFF 時の実 UI 経路）

| Item | Value |
|---|---|
| HTTP Status | **200** |
| `meta.contract_ok` | **true** |
| Guard 必須フィールド | single/detail と同型で充足 |
| Client Guard | **PASS** |

---

## 3. Contract Diff（本番レスポンス vs Guard）

| Guard Field | single/detail | ui/prediction-bundle | predictions | Rejected? |
|---|---|---|---|---|
| schema_version | `…/2.0` | `…/2.0` | `…/2.0` | **No** |
| race_id | string | string | string | **No** |
| race_info | object | object | object | **No** |
| race_info.venue | string `新潟` | string `unknown` | string `新潟` | **No** |
| race_info.date | string | string | string | **No** |
| race_info.race_no | number `11` | number `11` | number `11` | **No** |
| evaluation.runners | array(15) | array(0) | array(15) | **No** |
| ai_confidence.score | number | null | number | **No** |
| explain.narrative | string | string `""` | string | **No** |
| betting_recommendations.items | array | array | array | **No** |

**Contract Guard が弾いている実フィールド: なし（本番 API 経路）**

---

## 4. 全件スキャン

| Endpoint | Date | N | Guard FAIL |
|---|---|---|---|
| GET `/api/predictions/:id` | 2026-07-26 | 36 | **0** |
| POST `/api/single/detail/:id` | 2026-07-26 | 36 | **0** |

---

## 5. 結論（証拠ベース）

1. 本番の `/api/single/detail/:id` と `/api/ui/prediction-bundle` の **HTTP 200 レスポンスは現状 Guard を通過**する。  
2. `normalizePredictionBundle` / `ensurePredictionBundleContract` は single/detail・predictions で meta `contract_ok=true` として確認済み。  
3. したがって「PredictionBundle が契約と一致しません」が **今も出る場合、原因は当該本番レスポンス本体ではない**（別 race_id / キャッシュされた旧 bundle / 非 ADMIN の OPS_CLOSED 経路 / 別画面・別ビルド 等を要確認）。  
4. UI3 で修正した歴史的差分（`narrative` 欠落・`race_no` 非 number）は、**現本番レスポンスには残っていない**。

---

## 6. Decision

| Item | Value |
|---|---|
| Action Type | Evidence / Diagnose only |
| Implementation Required | **No**（本番 API Contract は PASS） |
| Deployment Required | No |
| Configuration Required | No（Flag `single_ai_detail` は OFF のまま） |
| Next | ユーザー再現 race_id / Network の実リクエスト URL・Response キャプチャを突き合わせ |
