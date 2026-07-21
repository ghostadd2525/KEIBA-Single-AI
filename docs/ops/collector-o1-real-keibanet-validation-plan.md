# O-1 — Real KeibaNet Validation Plan

**Series:** Operations（O）  
**Date:** 2026-07-21  
**Prerequisite:** Collector RC-1 PASS  
**Scope:** 計画のみ（本ドキュメント作成時点でコード変更・実接続は行わない）  
**Goal:** Real KeibaNet 実接続検証を完了し、**Version 1.0 / Go-Live** 判定材料を揃える

関連:

- RC-1: [`collector-rc1-release-review.md`](./collector-rc1-release-review.md)
- C-7: [`collector-c7-production-validation.md`](./collector-c7-production-validation.md)
- C-8: [`collector-c8-production-readiness.md`](./collector-c8-production-readiness.md)

---

## 0. 位置づけ

| 項目 | 内容 |
|------|------|
| 開発フェーズ | **終了**（C-0 … C-8 / RC-1） |
| 以降の管理 | **O シリーズ（Operations）** |
| 本計画 | **O-1** — Real KeibaNet Validation |
| 成功時の次 | Version 1.0 宣言 + Go-Live（条件は §5） |

---

## 1. 前提・入力

### 1.1 必須環境変数

| 変数 | 用途 | 備考 |
|------|------|------|
| `EXPECT_KEIBANET_BASE_URL` | 実 KeibaNet ベース URL | **未設定だと O-1 開始不可** |
| `EXPECT_COLLECT_DAILY_LIMIT` | Budget SoT（既定 150） | Client と共有 |
| `EXPECT_AI_DB_PATH` | 検証用 DB（本番と分離推奨） | 隔離必須 |
| `EXPECT_COLLECT_MANIFEST_DIR` | Manifest 出力先 | 隔離必須 |
| `EXPECT_COLLECT_RAW_DIR` | Raw Store | 隔離必須 |
| `EXPECT_KEIBANET_TIMEOUT` | タイムアウト秒（既定 30） | Timeout 試験で一時短縮可 |
| `EXPECT_KEIBANET_MAX_RETRIES` | トランスポート再試行 | 429/500 確認用 |
| `EXPECT_KEIBANET_MIN_INTERVAL_SEC` | リクエスト間隔 | Rate Limit 配慮 |

任意: `EXPECT_KEIBANET_USER_AGENT`

### 1.2 対象週・レース

実開催カレンダーから **検証用に 1 週 + 代表 1〜数レース** を選定する。

| 選定ルール | 内容 |
|------------|------|
| week_id | 土曜基準の開催週 |
| STATIC 検証日 | 月〜金（race_meta / 可能なら entries_core） |
| DYNAMIC 検証日 | 開催日当日（odds / track） |
| 最低件数 | 各 artifact **成功 1 件以上** |

**注意:** 本番 Budget を食い潰さないよう、O-1 中は `EXPECT_COLLECT_DAILY_LIMIT` を検証用に抑え、間隔を空ける。

### 1.3 非対象（本計画では実施しない）

- P2 / P3 artifact
- Prediction / FeatureLoader / LightGBM の改修
- systemd / 本番 Timer の恒久配線（確認のみ可）
- Collector 仕様変更

---

## 2. 実施手順

### Phase A — 準備（接続前）

1. 検証用ディレクトリ / DB / Manifest / Raw を本番から隔離して用意する  
2. `EXPECT_KEIBANET_BASE_URL` を設定し、疎通用に 1 GET（例: `race_meta` 1 レース）を実行する  
3. 応答が HTTP 層まで届くこと（認証・DNS・TLS・Firewall）を確認する  
4. RC-1 既知の Controlled スイートがローカルで緑であることを再確認する（回帰保険）  
5. 検証ログの保存先（日時・URL・status・所要時間）を決める  

**ゲート:** 疎通失敗なら Phase B に進まない → §4 切り分けへ。

### Phase B — 接続確認（G1）

1. BASE_URL 解決・TLS・HTTP 応答コードを記録  
2. User-Agent / Timeout / min_interval が意図どおりか確認  
3. Client と Scheduler が **同一 `CollectBudget`** を参照する運用コマンド／スクリプト手順を文書化する  

**成果物:** 接続ログ 1 セット（成功または失敗理由）

### Phase C — 4 artifact 成功取得（G2）

各 artifact について、実 API から取得 → Validator → READY を確認する。

| 順 | artifact | 推奨タイミング | 成功の定義 |
|----|----------|----------------|------------|
| 1 | `race_meta` | 平日 | HTTP 2xx + Validator PASS + job READY + Raw 存在 |
| 2 | `entries_core` | 枠順確定後 | 同上（entries 必須フィールド充足） |
| 3 | `odds` | 開催日 | 同上 |
| 4 | `track` | 開催日 | 同上 |

手順（各 artifact 共通）:

1. Planner（または最小 seed）で対象ジョブを PENDING にする  
2. Scheduler.dequeue（Budget 消費を記録）  
3. Collector.run_job  
4. job status / artifact / raw_path / Manifest 更新を記録  

### Phase D — 失敗系（G3）

実 API で誘発できない項目は **ステージング同等の故障注入** または **一時的な不正 path / 極端 Timeout** で代替し、その旨をレポートに明記する。

| シナリオ | 狙い | 期待 |
|----------|------|------|
| HTTP 429 | Rate Limit | Client 再試行後 FAILED、`retry_after` 自動設定 |
| HTTP 500 | サーバ障害 | 同上 |
| Timeout | 遅延 / 遮断 | FAILED + `retry_after` |
| （参考）Partial | 必須欠落レスポンス | PARTIAL + `retry_after` |

その後:

1. `CollectRetry.process(as_of_date=retry_after)`  
2. status が **PENDING** に戻ることを確認  
3. 再取得で READY または再 FAILED を記録（上限 attempt 内）

### Phase E — Budget / Retry / Manifest / OPS（G4, G5, G7）

1. **Budget:** 1 日分の dequeue 前後で Manifest `budget.daily_limit/used/remaining` が Scheduler・Client と一致  
2. **Retry:** Phase D の自動再投入が Manifest `collect.partial/failed/retry` に反映  
3. **Weekday 分散（G5）:** 実カレンダー 1 週で `scheduled_for` が月〜金に分かれ、1 日件数が `daily_limit` を計画上超えない（超過時は spill 挙動を記録）  
4. **OPS:** `evaluate_collect_ops`（または同等）で Prediction 軸と DYNAMIC 軸が Manifest と矛盾しない  

### Phase F — Prediction 非破壊（G6）

1. 検証対象 race について Collector 導入前（または ETL 前）の Prediction シグネチャを取得  
2. READY な STATIC を ETL Bridge（`ingest_ready_race_meta` 等）へ投入  
3. 同一 race の Prediction シグネチャを再取得  
4. **top / engine_source 等が一致**することを合格とする  

推奨: real engine が使える環境では real でも実施。不可なら mock で実施し「mock 限定 PASS」と明記。

### Phase G — 締め・判定

1. 下記 §3 チェックリストをすべて埋める  
2. §5 の Version 1.0 昇格条件を評価する  
3. 結果を `docs/ops/collector-o1-real-keibanet-validation-report.md`（実施後に作成）へ残す  

---

## 3. 確認項目チェックリスト

実施時に □ を ☑ へ更新する。

### 接続

- [ ] `EXPECT_KEIBANET_BASE_URL` 設定済み  
- [ ] DNS / TLS / HTTP 疎通成功  
- [ ] 隔離 DB / Manifest / Raw 使用  

### 4 artifact

- [ ] `race_meta` READY  
- [ ] `entries_core` READY  
- [ ] `odds` READY  
- [ ] `track` READY  

### 失敗系

- [ ] 429 → FAILED + retry_after  
- [ ] 500 → FAILED + retry_after  
- [ ] Timeout → FAILED + retry_after  
- [ ] CollectRetry → PENDING  

### Budget / Manifest / OPS

- [ ] Budget SoT 一致（Manifest = Scheduler = Client）  
- [ ] Manifest schema 1.1 妥当  
- [ ] OPS Prediction 軸が Gate 結果と一致  
- [ ] OPS DYNAMIC 軸が dynamic_* と矛盾しない  
- [ ] 平日 `scheduled_for` 分散を実週で確認  

### Prediction

- [ ] Collector/ETL 前後で Prediction シグネチャ不変  

---

## 4. 合格基準（G1〜G7）

RC-1 で定義した Go-Live ゲートと同一。**すべて PASS で O-1 合格。**

| ID | 基準 | 合格の定義 |
|----|------|------------|
| **G1** | BASE_URL 設定・接続 | 実ホストへ到達し、意図した API から応答を得られる |
| **G2** | 4 artifact 成功 | race_meta / entries_core / odds / track が各 1 件以上 READY |
| **G3** | 429 / 5xx / Timeout → retry | FAILED（または Timeout 由来 FAILED）+ `retry_after` → CollectRetry で PENDING |
| **G4** | Budget 一致 | Manifest / Scheduler / Client の daily_limit・used・remaining が同一 SoT 上で一致 |
| **G5** | 平日分散 | 実カレンダー週で WEEKDAY ジョブの `scheduled_for` が月〜金に計画分散される |
| **G6** | Prediction 非破壊 | ETL 前後で Prediction シグネチャが一致 |
| **G7** | OPS 健全 | Prediction 軸・DYNAMIC 軸が Manifest と整合（誤表示なし） |

| O-1 総合 | 条件 |
|----------|------|
| **O-1 PASS** | G1〜G7 すべて PASS |
| **O-1 HOLD** | いずれか未達。未達 ID と切り分け結果を報告 |

---

## 5. Version 1.0 へ昇格する条件

次を **すべて** 満たしたとき、Collector を **Version 1.0** および **Go-Live** として宣言してよい。

1. **O-1 PASS**（G1〜G7）  
2. Known Limitation の **Must** が Real KeibaNet 関連で残っていないこと  
3. 実施レポート（証拠: 日時・週・race・HTTP 結果・Manifest 抜粋）がリポジトリまたは OPS 保管場所に残っていること  
4. ステークホルダーが「本番 Budget・間隔・対象週」に合意していること  

昇格時の推奨アクション（実施は O-1 後の運用タスク）:

- タグ例: `collector-1.0.0`  
- RC-1 ドキュメントに「1.0 昇格日 / O-1 レポートリンク」を追記  
- Go-Live HOLD を解除  

**満たさない場合:** `collector-rc-1` のまま。1.0 宣言禁止。

---

## 6. 失敗時の切り分け手順

### 6.1 接続できない（G1 失敗）

| 順 | 確認 |
|----|------|
| 1 | URL スキーム / ホスト / パス typo |
| 2 | DNS / VPN / 社内 FW / TLS 証明書 |
| 3 | 認証・IP allowlist（必要な場合） |
| 4 | ローカル Controlled mock がまだ緑か（回帰切り分け） |
| 5 | 別ネットワークまたはステージング URL で再現 |

→ 環境問題なら Collector 改修不要。接続可能になるまで O-1 HOLD。

### 6.2 artifact が READY にならない（G2 失敗）

| 観測 | 切り分け |
|------|----------|
| HTTP 4xx/5xx | 実 API 契約・path・クエリ（date/venue/race_no）を確認 |
| HTTP 200 だが PARTIAL | Validator 必須フィールド vs 実レスポンス差分を記録（**仕様変更は別承認**） |
| FAILED + timeout | `EXPECT_KEIBANET_TIMEOUT` / 回線 / サーバ遅延 |
| ジョブ未生成 | Availability（WEEKDAY / AFTER_DRAW / RACE_DAY）と as_of を確認 |

### 6.3 Retry が PENDING に戻らない（G3 失敗）

| 順 | 確認 |
|----|------|
| 1 | job.`retry_after` がセットされているか |
| 2 | `CollectRetry` の `as_of_date` ≥ `retry_after` か |
| 3 | `attempt` ≥ `max_attempts` でスキップされていないか |
| 4 | 状態が FAILED/PARTIAL 以外になっていないか |

### 6.4 Budget 不一致（G4 失敗）

| 順 | 確認 |
|----|------|
| 1 | Client と Scheduler が **同一 CollectBudget インスタンス**を共有しているか |
| 2 | 旧 `EXPECT_KEIBANET_DAILY_LIMIT` だけが残って SoT とズレていないか |
| 3 | Manifest 更新が Scheduler.finish 前か後か |

### 6.5 分散が崩れる（G5 失敗）

| 順 | 確認 |
|----|------|
| 1 | Planner に `scheduled_for` 固定上書きをしていないか |
| 2 | artifact が RACE_DAY / AFTER_DRAW のみで WEEKDAY が無い週になっていないか |
| 3 | week_id（土曜基準）と曜日ウィンドウの対応 |

### 6.6 Prediction が変わった（G6 失敗）

| 順 | 確認 |
|----|------|
| 1 | 比較した race_id が同一か |
| 2 | ETL が features / モデル入力を書き換えていないか（設計上は races 等のみ） |
| 3 | engine（mock/real）切替が混在していないか |
| 4 | **Collector 改修前に**差分原因を ETL / データ側で切り分ける |

### 6.7 OPS 不整合（G7 失敗）

| 順 | 確認 |
|----|------|
| 1 | Friday Gate 実行有無（prediction_* 正本） |
| 2 | Scheduler が prediction_* を誤更新していないか |
| 3 | dynamic_* と Prediction 軸の取り違え表示 |

---

## 7. 実施体制・成果物（実施時）

| 役割 | 内容 |
|------|------|
| 実施者 | Operations / Collector 担当 |
| 所要（目安） | 半日〜1 開催週（DYNAMIC は開催日依存） |
| 計画書 | **本ドキュメント（O-1）** |
| 実施レポート | 実施後に別文書で作成（合格/HOLD・G1〜G7 証跡） |

実施レポートに含める最低項目:

- 実施日時・環境・BASE_URL（秘匿はマスク可）  
- 対象 week_id / race  
- G1〜G7 判定表  
- 失敗時切り分け結果  
- Version 1.0 昇格の可否  

---

## 8. まとめ

| 項目 | 内容 |
|------|------|
| O-1 目的 | Real KeibaNet 実接続で G1〜G7 を証明する |
| 合格 | G1〜G7 すべて PASS |
| 1.0 昇格 | O-1 PASS + Must 解消 + 証跡保管 + 合意 |
| 本ドキュメント | **計画のみ**（コード変更なし） |
