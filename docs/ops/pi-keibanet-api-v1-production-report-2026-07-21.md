# PI API Version 1 — 本番反映レポート

**Date:** 2026-07-21 20:47 JST  
**Target:** EC2 本番（`ubuntu@13.231.5.5` / `ip-172-31-40-147`）  
**Service:** `expect-pi-keibanet-api.service`（port **8081**）  
**Backup:** `/var/backups/expect-ai/pi-keibanet-api/20260721T204619`

---

## 1. デプロイ成功可否

| 項目 | 結果 |
|------|------|
| バックアップ作成 | **成功** |
| コード反映 | **成功** |
| systemd 更新・再起動 | **成功** |
| スモークテスト | **6/6 PASS** |
| 公開レース Prediction | **9/9 成功** |

**総合判定: デプロイ成功（GO）**

---

## 2. 起動確認

| 確認 | 結果 |
|------|------|
| `systemctl is-active expect-pi-keibanet-api` | **active** |
| `GET /health` | **200** `{"status":"ok","service":"pi-keibanet-api"}` |
| `expect-ai`（Web API / Python AI） | **active** |
| `GET http://127.0.0.1:8000/health` | **200** |

---

## 3. Prediction 確認

| レース（2026-07-25） | race_id | prediction_available |
|----------------------|---------|-------------------|
| 新潟6R | 2026-07-25-01-06 | ✅ |
| 新潟7R | 2026-07-25-01-07 | ✅ |
| 新潟8R | 2026-07-25-01-08 | ✅ |
| 中京6R | 2026-07-25-02-06 | ✅ |
| 中京7R | 2026-07-25-02-07 | ✅ |
| 中京8R | 2026-07-25-02-08 | ✅ |
| 札幌10R | 2026-07-25-03-10 | ✅ |
| 札幌11R | 2026-07-25-03-11 | ✅ |
| 札幌12R | 2026-07-25-03-12 | ✅ |

**9/9 成功** — FeatureLoader → CorePipeline → Candidate Evaluation まで正常。

---

## 4. API 確認

| エンドポイント | HTTP | 結果 |
|----------------|------|------|
| `GET /v1/races?date=2026-07-25` | 200 | venues=3, races=9（公開済みのみ） |
| `GET /v1/races/2026-07-25-01-06` | 200 | race_id / race_label 正常 |
| `GET /v1/predictions/2026-07-25-01-06` | 200 | prediction_available=true |
| `GET /v1/static/race_meta`（Collector） | 200 | Validator OK |
| `GET /v1/static/entries_core`（Collector） | 200 | Validator OK |

**ユニットテスト:** `tests.test_web_races_api` **10/10 PASS**

---

## 5. Web 確認

| 項目 | 結果 |
|------|------|
| PI API Web ルート（`/v1/races`, `/v1/predictions`） | **新規エンドポイント稼働** |
| expect-ai（BFF 向け Python AI） | **稼働中**（影響なし） |
| Collector `EXPECT_KEIBANET_BASE_URL` | `http://127.0.0.1:8081`（変更なし） |

---

## 6. 未公開レース

| 確認 | 結果 |
|------|------|
| 一覧 `/v1/races?date=2026-07-25` | 公開9レースのみ（未公開27レースは非表示） |
| 未公開 `GET /v1/predictions/2026-07-25-01-01` | **404** `race_not_found` / `race_no_mismatch`（システムエラーなし） |

未公開レースはエラー（500）にならず、404 + 理由コードで返却。**要件充足。**

---

## 7. ログ

`journalctl -u expect-pi-keibanet-api` — 起動・リクエスト正常。Prediction 実行時に pandas UserWarning（正規表現）のみ。致命エラーなし。

---

## 8. 反映内容

### バックアップ（ロールバック用）

```
/var/backups/expect-ai/pi-keibanet-api/20260721T204619/
├── service/                    # 旧 PI API コード全体
├── expect-pi-keibanet-api.service
├── collect.env
└── platform_data/              # /opt/expect-ai/platform/data スナップショット
```

### デプロイ

- `services/pi-keibanet-api/` — Version 1（Web API + Collector 拡張）
- 新規: `race_catalog.py`, Web ルート, numpy JSON シリアライズ
- `service.py` — 本番パス解決（`PI_AI_PLATFORM_ROOT`, `PI_DATA_ROOT`）
- systemd — 環境変数追加
- データ — `demo_daily_outputs/2026-07-25/` を `/opt/expect-ai/platform/data/` へ同期

### systemd 環境変数（追加）

```
PI_AI_PLATFORM_ROOT=/opt/expect-ai/platform
PI_DATA_ROOT=/opt/expect-ai/platform/data
```

---

## 9. 問題点

| # | 内容 | 深刻度 |
|---|------|--------|
| 1 | Prediction 時 pandas UserWarning（既存ロジック） | 低（動作に影響なし） |
| 2 | features CSV は 2026-07-25 分のみ同期済み。他日付は Collector/pipeline 実行後に daily CSV 生成が必要 | 運用注意 |
| 3 | EC2 git 上 `services/pi-keibanet-api/` は未コミット（手動 scp 反映） | 中（次回 git pull 連携推奨） |

---

## 10. ロールバック要否

**不要（現時点）**

異常時のロールバック手順:

```bash
BACKUP=/var/backups/expect-ai/pi-keibanet-api/20260721T204619
sudo cp -a $BACKUP/service /home/ubuntu/KEIBA-Single-AI/services/pi-keibanet-api
sudo cp $BACKUP/expect-pi-keibanet-api.service /etc/systemd/system/
sudo cp -a $BACKUP/platform_data /opt/expect-ai/platform/data
sudo systemctl daemon-reload
sudo systemctl restart expect-pi-keibanet-api
curl -sS http://127.0.0.1:8081/health
```

---

## 11. 検証コマンド（再実行用）

```bash
cd /home/ubuntu/KEIBA-Single-AI/services/pi-keibanet-api
python3 scripts/prod_smoke.py
python3 -m unittest tests.test_web_races_api -v
EXPECT_KEIBANET_BASE_URL=http://127.0.0.1:8081 python3 scripts/ec2_client_validate.py
```

---

**署名:** PI API Version 1 本番反映 — 2026-07-21 20:47 JST — **GO**
