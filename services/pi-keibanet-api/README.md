# PI KeibaNet API

Raspberry Pi 上で netkeiba HTML を取得し、SingleAI Collector および Web GUI 向け JSON API を提供します。

## Quick start

```bash
cd services/pi-keibanet-api
python3 run.py

# Collector（従来）
curl -sS "http://127.0.0.1:8081/v1/static/race_meta?date=2026-07-25&venue=%E6%96%B0%E6%BD%9F&race_no=6"

# Web GUI: 開催日 → 会場 → レース一覧
curl -sS "http://127.0.0.1:8081/v1/races?date=2026-07-25"

# Web GUI: レース詳細（Prediction キー = race_id）
curl -sS "http://127.0.0.1:8081/v1/races/2026-07-25-01-06"

# Web GUI: 予測
curl -sS "http://127.0.0.1:8081/v1/predictions/2026-07-25-01-06"
```

## Web GUI API（推奨）

| Method | Path | 用途 |
|--------|------|------|
| GET | `/v1/races?date=YYYY-MM-DD` | 会場ごとのレース一覧 |
| GET | `/v1/races/{race_id}` | レース詳細（表示用メタ） |
| GET | `/v1/predictions/{race_id}` | Prediction（race_id キー） |

### レスポンス共通フィールド（表示・選択用）

| フィールド | 例 | 説明 |
|------------|-----|------|
| `race_id` | `2026-07-25-01-06` | Prediction キー（Win5 形式） |
| `race_date` | `2026-07-25` | 開催日 |
| `course` | `新潟` | 会場（削除しない） |
| `race_number` | `6` | レース番号（削除しない） |
| `race_label` | `新潟6R` | GUI 表示用 |
| `race_name` | `豊栄特別` | レース名（取得できる場合） |

`venue` / `race_no` は Collector 互換のエイリアスとして併記します。

### 一覧レスポンス構造例

```json
{
  "date": "2026-07-25",
  "venues": [
    {
      "course": "新潟",
      "races": [
        {"race_id": "2026-07-25-01-06", "race_label": "新潟6R", "race_number": 6, "race_name": "豊栄特別"}
      ]
    }
  ],
  "races": ["...flat list..."]
}
```

フロントエンドは `venues[]` を使って「会場 → レース」選択 UI を構築し、選択後は `race_id` で詳細・予測を呼びます。

## Collector 接続

EC2 / SingleAI 側:

```bash
EXPECT_KEIBANET_BASE_URL=http://{PI_HOST}:8081
```

従来エンドポイント（`/v1/static/*`, `/v1/dynamic/*`）は維持。レスポンスに `course` / `race_number` / `race_label` を追加済みです。

## 仕様書

[`docs/ops/pi-keibanet-api-spec.md`](../../docs/ops/pi-keibanet-api-spec.md)

## テスト

```bash
python3 -m unittest tests.test_pi_api tests.test_web_races_api -v
```

## systemd（PI / EC2 暫定）

**Raspberry Pi（本番想定）**

```bash
sudo cp infra/pi/systemd/expect-pi-keibanet-api.service /etc/systemd/system/
sudo systemctl enable --now expect-pi-keibanet-api
```

**EC2 上で暫定ブリッジとして動かす場合**（PI 未到着時）:

```bash
sudo cp infra/aws/systemd/expect-pi-keibanet-api.service /etc/systemd/system/
sudo systemctl enable --now expect-pi-keibanet-api
# collect.env: EXPECT_KEIBANET_BASE_URL=http://127.0.0.1:8081
```

### 公開レース自動更新（Phase A）

```bash
sudo cp infra/aws/systemd/expect-pi-race-refresh.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now expect-pi-race-refresh.timer
```

| Unit | 役割 |
|------|------|
| `expect-pi-race-refresh.timer` | 15分ごと（08:00–20:00 JST はスクリプト側で判定） |
| `expect-pi-race-refresh.service` | 公開レース差分 → entries → history → features |

手動実行:

```bash
cd services/pi-keibanet-api
python3 scripts/prod_race_refresh.py --date 2026-07-25 --force
```

ログ: `journalctl -u expect-pi-race-refresh.service`  
JSON: `$PI_DATA_ROOT/var/race_refresh/{date}/logs/refresh_latest.json`

### 全日特徴量の安全拡張（未勝利・新馬含む）

**運用正本:** [`docs/ops/v2-operations-race-refresh-addendum.md`](../../docs/ops/v2-operations-race-refresh-addendum.md)

要約:

1. **現行 shutuba を正**とする（旧 CSV 頭数より名簿を優先）
2. features 行数は runners と一致
3. fingerprint 変化レースは再生成
4. Shadow 比較でガード頭数減少 → **切替禁止**
5. Production 一括反映は最終確定出馬表タイミング + Shadow 承認後

```bash
# 1) Shadow に生成（本番 CSV は上書きしない）
python3 scripts/prod_race_refresh.py --date 2026-07-25 --force \
  --shadow-dir /tmp/pi-features-shadow

# 2) 比較（頭数減少時は exit != 0 / 切替しない）
python3 scripts/compare_daily_features.py --date 2026-07-25 \
  --baseline "$PI_DATA_ROOT/demo_daily_outputs/2026-07-25/demo_runners_pace_market_features.csv" \
  --candidate "/tmp/pi-features-shadow/demo_daily_outputs/2026-07-25/demo_runners_pace_market_features.csv"

# 3) ゲート PASS + 人間承認後のみ原子的置換（Addendum §5）
```

環境変数 `PI_FEATURES_SHADOW_DIR` でも shadow 出力先を指定できます。

## netkeiba 取得

レース一覧は JS 描画のため `race_list_sub.html?kaisai_date=YYYYMMDD` を使用（仕様書 §6 参照）。
