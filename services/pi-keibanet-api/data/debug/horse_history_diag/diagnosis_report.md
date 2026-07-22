# 馬戦績取得失敗 — 原因切り分けレポート

**調査日:** 2026-07-21  
**対象馬:** ジェットブレード (`horse_id=2022103522`)  
**比較対象レース:** 2026-07-19 福島10R（numeric_race_id=202603020810）

---

## 結論（先に）

| 仮説 | 判定 | 根拠 |
|------|------|------|
| HTML構造変更でパーサが壊れた | **否** | AJAX レスポンスでは既存 regex / BS4 両方パース成功 |
| regex 不足で BS4 なら取れる | **否** | 初回 HTML にはテーブル自体が無く、BS4 でも 0 行 |
| JavaScript 描画で初回 HTML に無い | **是（部分）** | 戦績は jQuery AJAX で後注入。ただし **Selenium 不要** |
| Selenium 移植が必要 | **不要** | `ajax_horse_results.html` を requests で直接取得可能 |

**根本原因:** PI API は `db.netkeiba.com/horse/{id}/` の**初回 HTML のみ**をパースしている。  
戦績テーブルは初回 HTML に含まれず、`ajax_horse_results.html?id={horse_id}` の AJAX レスポンス（JSON → HTML 断片）に存在する。

**推奨修正:** Selenium ではなく、Legacy と同じデータ源に到達するため **AJAX エンドポイントを追加 fetch** する。

---

## 1. requests で取得した HTML の保存

| ファイル | URL | サイズ |
|---------|-----|--------|
| `horse_2022103522_requests.html` | `https://db.netkeiba.com/horse/2022103522/` | 68,737 bytes |
| `horse_2022103522_ajax.json` | `https://db.netkeiba.com/horse/ajax_horse_results.html?...` | 116,753 bytes |
| `horse_2022103522_ajax_fragment.html` | 上記 JSON の `data` フィールド | 101,097 bytes |

保存先: `data/debug/horse_history_diag/`

---

## 2. 初回 HTML に戦績テーブルが存在するか

### requests 初回 HTML (`horse_2022103522_requests.html`)

| チェック項目 | 結果 |
|-------------|------|
| `<table>` 数 | **1**（プロフィール表 `db_prof_table` のみ） |
| `class="db_h_race_results"` | **False** |
| `<th>日付</th>` | **False** |
| `<th>着順</th>` | **False** |
| `#horse_results_box` プレースホルダ | **True**（空コンテナ） |
| `ajax_horse_results.html` 参照 | **True**（jQuery `$.get` で後読み込み） |

→ **初回 HTML には戦績テーブルが存在しない。**

### Legacy Selenium キャッシュ (`demo_bundle_cache/horse_2022103522.html`)

| チェック項目 | 結果 |
|-------------|------|
| `<table>` 数 | **4** |
| `class="db_h_race_results"` | **True** |
| `<th>日付</th>` | **True** |
| 戦績データ行 | **20行** |

→ Selenium は JS 実行後の DOM（AJAX 注入後）を `page_source` として取得している。

---

## 3. DOM パーサ（BeautifulSoup）で取得できるか

| HTML ソース | BS4 テーブル検出 | Legacy `parse_history_rows_from_bs4_table` | PI regex パーサ |
|------------|-----------------|-------------------------------------------|----------------|
| requests 初回 HTML | **なし** | **0 行** | **0 行** |
| AJAX fragment | **あり** | **21 行** | **21 行** |
| Legacy Selenium キャッシュ | **あり** | **20 行** | **20 行** |

→ テーブルが HTML に存在すれば **regex でも BS4 でもパース可能**。  
失敗原因はパーサ種別ではなく、**パース対象 HTML にテーブルが無い**こと。

---

## 4. JavaScript 描画の確認

初回 HTML 内の該当コード（`horse_2022103522_requests.html` L1082-1092）:

```javascript
$.get('https://db.netkeiba.com/horse/ajax_horse_results.html',
{
  input: 'UTF-8',
  output: 'json',
  id: horse_id,
},
function(data){
  if('OK' == data.status){
    $('#horse_results_box').html(data.data);
  }
});
```

| 項目 | 内容 |
|------|------|
| 描画方式 | jQuery AJAX（React/Vue/SPA ではない） |
| 注入先 | `#horse_results_box` |
| データ URL | `https://db.netkeiba.com/horse/ajax_horse_results.html` |
| パラメータ | `input=UTF-8&output=json&id={horse_id}` |
| レスポンス形式 | `{"status":"OK","data":"<html断片>"}` |

### AJAX 直接 fetch の結果（requests のみ）

| horse_id | ajax status | regex パース行数 |
|----------|-------------|-----------------|
| 2022103522 | OK | 21 |
| 2022104635 | OK | 10 |
| 2017101772 | OK | 41 |

→ **AJAX エンドポイントは requests だけで取得・パース可能。**

---

## 5. Selenium 移植の要否

| 条件 | 該当 |
|------|------|
| 初回 HTML にテーブル無し | ✅ |
| JS 描画（AJAX 後注入） | ✅ |
| AJAX URL を requests で代替可能 | ✅ |
| **Selenium 必要** | **❌ 不要** |

Legacy Win5AI（Selenium）が取得していたのは、ブラウザ内で AJAX 実行後の DOM。  
同等データは **`ajax_horse_results.html` の直接 fetch** で再現できる。

---

## 原因分類

| 分類 | 該当 |
|------|------|
| netkeiba 側仕様（AJAX 分離） | ✅ 初回 HTML と AJAX でコンテンツ分離 |
| パース差異（regex vs BS4） | ❌ テーブルがあれば両方動作 |
| PI 実装不足（fetch URL 不足） | ✅ 初回 HTML のみ fetch していた |
| Selenium 必須 | ❌ |

---

## 推奨次アクション

1. `horse_history.py` の `fetch_horse_history()` を修正  
   - `ajax_horse_results.html?id={horse_id}` を fetch  
   - JSON の `data` フィールドを既存パーサに渡す
2. Selenium は導入しない
3. 修正後、`compare_win5ai_vs_pi.py` で horse_history / features 一致率を再計測

---

## 添付ファイル一覧

```
data/debug/horse_history_diag/
  horse_2022103522_requests.html      # requests 初回 HTML
  horse_2022103522_ajax.json          # AJAX JSON 生レスポンス
  horse_2022103522_ajax_fragment.html # AJAX data 断片（戦績テーブル含む）
  diagnosis_report.md                 # 本レポート
```
