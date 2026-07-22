# PI KeibaNet API — 仕様書

**Version:** 1.0  
**Date:** 2026-07-21  
**Role:** Raspberry Pi（PI環境）上で netkeiba を取得し、SingleAI Collector 契約 JSON を提供するブリッジ API

---

## 1. 位置づけ

```
netkeiba (HTML)
    ↓ fetch + parse (PI)
PI KeibaNet API (JSON, Collector 契約)
    ↓ EXPECT_KEIBANET_BASE_URL
SingleAI Collector → Raw → ETL → SQLite
```

- Collector **契約は変更しない**
- PI が `/v1/static/*` / `/v1/dynamic/*` を実装
- 認証なし（LAN / VPN 内運用。必要ならリバースプロキシで保護）

---

## 2. ベース URL

| 環境 | 例 |
|------|-----|
| PI ローカル | `http://127.0.0.1:8081` |
| EC2 → PI（同一 VPC / VPN） | `http://{PI_LAN_IP}:8081` |

Collector 設定:

```bash
EXPECT_KEIBANET_BASE_URL=http://192.168.1.50:8081
```

---

## 3. 共通

| 項目 | 値 |
|------|-----|
| Protocol | HTTP/1.1 |
| Method | GET |
| Response | `application/json; charset=utf-8` |
| Auth | なし |
| Request headers（Collector 側） | `User-Agent`, `Accept: */*` |

### Query（全エンドポイント共通）

| パラメータ | 必須 | 例 | 説明 |
|------------|------|-----|------|
| `date` | Yes | `2026-07-25` | 開催日 |
| `venue` | Yes | `新潟`（URL エンコード可） | 競馬場名（日本語） |
| `race_no` | Yes | `1` | レース番号 1–12 |

---

## 4. エンドポイント

### 4.1 `GET /health`

疎通確認。

**Response 200**

```json
{"status": "ok", "service": "pi-keibanet-api"}
```

---

### 4.2 `GET /v1/static/race_meta`

**Response 200 — 例**

```json
{
  "race_id": "20260725_01_新潟",
  "date": "2026-07-25",
  "venue": "新潟",
  "race_no": 1,
  "distance": 1600,
  "surface": "芝",
  "race_name": "3歳未勝利",
  "field_size": 16
}
```

| フィールド | Collector 必須 |
|------------|----------------|
| race_id, date, venue, race_no, distance | **Yes** |
| surface, race_name, field_size | No（ETL で利用可） |

---

### 4.3 `GET /v1/static/entries_core`

**Response 200 — 例**

```json
{
  "race_id": "20260725_01_新潟",
  "date": "2026-07-25",
  "venue": "新潟",
  "race_no": 1,
  "entries": [
    {
      "horse_number": 1,
      "frame": 1,
      "horse_name": "サンプルA",
      "jockey": "騎手A",
      "weight": 55.0,
      "horse_id": "2023100001"
    }
  ]
}
```

| entry フィールド | Collector 必須 |
|------------------|----------------|
| horse_number, frame, horse_name, jockey, weight | **Yes** |
| horse_id | No（ETL で利用可） |

---

### 4.4 `GET /v1/dynamic/odds`

**Response 200 — 例**

```json
{
  "race_id": "20260725_01_新潟",
  "date": "2026-07-25",
  "venue": "新潟",
  "race_no": 1,
  "odds": [
    {"horse_number": 1, "win": 2.5},
    {"horse_number": 2, "win": 5.1}
  ]
}
```

---

### 4.5 `GET /v1/dynamic/track`

**Response 200 — 例**

```json
{
  "race_id": "20260725_01_新潟",
  "date": "2026-07-25",
  "venue": "新潟",
  "race_no": 1,
  "condition": "良"
}
```

`condition`: `良` / `稍重` / `重` / `不良`

---

## 5. エラーレスポンス

| HTTP | 意味 |
|------|------|
| 400 | Query 不足 / 形式不正 |
| 404 | netkeiba 上に該当レースなし |
| 502 | netkeiba 取得失敗 |

```json
{"error": "race_not_found", "message": "..."}
```

---

## 6. netkeiba 取得元

| 用途 | URL |
|------|-----|
| レース一覧 | `https://race.netkeiba.com/top/race_list_sub.html?kaisai_date=YYYYMMDD` |
| 出走表 | `https://race.netkeiba.com/race/shutuba.html?race_id={12桁}` |

`race_id` 12 桁: 桁 `[4:6]` = 競馬場コード、`[-2:]` = レース番号

| コード | 場 |
|--------|-----|
| 01 | 札幌 |
| 02 | 函館 |
| 03 | 福島 |
| 04 | 新潟 |
| 05 | 東京 |
| 06 | 中山 |
| 07 | 中京 |
| 08 | 京都 |
| 09 | 阪神 |
| 10 | 小倉 |

---

## 7. PI 環境変数

| 変数 | 既定 | 説明 |
|------|------|------|
| `PI_KEIBANET_HOST` | `0.0.0.0` | バインド |
| `PI_KEIBANET_PORT` | `8081` | ポート |
| `PI_NETKEIBA_TIMEOUT` | `25` | netkeiba タイムアウト秒 |
| `PI_NETKEIBA_MIN_INTERVAL_SEC` | `1.0` | リクエスト間隔 |
| `PI_NETKEIBA_DEBUG_DIR` | — | 指定時、取得 HTML を保存（調査用） |

取得 URL は常に stdout へ `[pi-keibanet] fetch ...` として出力されます。

---

## 7.1 netkeiba レース一覧の注意

`race_list_sub.html` は **当日の一部レースのみ** を返すことがあります（例: 2026-07-25 は 6–8R / 10–12R のみ）。

PI API は以下で補完します:

1. `race_list_sub.html` + `race.sp.netkeiba.com` の race_id マージ
2. 会場ヘッダ（`2回 新潟 1日目`）から race_id を **構築**（`YYYY + 場コード + 回 + 日 + R`）

---

## 7.2 404 理由コード

| `reason` | 意味 |
|----------|------|
| `venue_name_mismatch` | 会場名が JRA コード表にない |
| `race_no_mismatch` | 一覧・構築のいずれでも race_id を解決できない |
| `shutuba_empty` | shutuba ページに出走表コンテンツなし（netkeiba 側未公開） |
| `parse_entries_empty` | shutuba はあるが出走馬パース結果 0 件 |
| `html_fetch_failed` (502) | netkeiba HTTP 取得失敗 |

---

## 8. 起動

```bash
cd services/pi-keibanet-api
python3 run.py
# → http://0.0.0.0:8081
```

systemd: `infra/pi/systemd/expect-pi-keibanet-api.service`

---

## 9. Collector 互換性

- ETL / FeatureBuilder / Prediction: **変更なし**
- `race_meta` / `entries_core` のみ SQLite 投入（既存どおり）
- Validator（C-1/C-4）PASS する JSON を返却することが要件

---

## 10. 実装

| パス | 内容 |
|------|------|
| `services/pi-keibanet-api/pi_keibanet/server.py` | HTTP サーバ |
| `services/pi-keibanet-api/pi_keibanet/service.py` | オーケストレーション |
| `services/pi-keibanet-api/pi_keibanet/netkeiba/` | fetch + parse |
| `services/pi-keibanet-api/tests/test_pi_api.py` | 契約テスト |
