# Version10.1 Audit — Data Source Feasibility（Research Collector）

**Date:** 2026-07-27 (JST)  
**Type:** 実データ取得可能性の証明（設計ではない）  
**Scope:** Prediction Logic / PE / CE / AI **変更なし**。Research Collector が取り得るソースのみ。  
**Probe host:** EC2 `ubuntu@13.231.5.5`（本番 AI と同系統の egress）  
**Artifacts:** `/tmp/v101-feasibility/`（`rates.json`, `extract_report.json`, `final_probe.json`, HTML サンプル）

---

## 0. Verdict（一目）

| Feature | 実取得 | 方法 | 成功率（本プローブ） | Collector 実装可 |
|---------|--------|------|---------------------:|------------------|
| trainer（調教師） | **YES** | Horse DB 静的 HTML | **5/5 (100%)** | **YES** |
| owner（馬主） | **YES** | Horse DB 静的 HTML | **5/5 (100%)** | **YES** |
| breeder（生産者） | **YES** | Horse DB 静的 HTML | **5/5 (100%)** | **YES** |
| sale_price（セリ取引価格） | **PARTIAL** | Horse DB 静的 HTML | フィールド **5/5** / 非 `-` **2/5** | **YES**（欠損は正規値） |
| sire（父） | **YES** | AJAX `ajax_horse_pedigree.html` | **5/5 (100%)** | **YES** |
| damsire（母父） | **YES** | 同上 | **5/5 (100%)** | **YES** |
| pedigree（血統表） | **YES** | 同上（`blood_table` HTML） | **5/5 (100%)** | **YES** |
| 調教タイム | **YES** | `oikiri.html?type=1` 静的 HTML | **13/14 (93%)** ※1 | **YES** |
| 調教評価（文言+字母） | **YES** | 同上 | **13/14 (93%)** ※1 | **YES** |
| 一番時計 | **PARTIAL** | `training_best_time.html` | 無料枠のみ（大半マスク） | **条件付き** |
| 調教偏差値（調子偏差値） | **YES** ※2 | `barometer/score.html` 静的 HTML | **10/10 (100%)** ※2 | **YES（要注意）** |

※1 対象レース: `race_id=202601010205`（2026-07-26 札幌 5R）。調教未公開馬 1 頭は空行。  
※2 同レースの **確定後ページ** で「今回 偏差値」列を取得。レース前ページの単独プローブは未実施（後述）。

**総合:** Horse DB 系は **取得可能を実データで証明**。調教タイム／評価も **非ログイン HTML から取得可能を証明**。一番時計は **プレミアム壁が主**。調子偏差値は HTML に数値が載ることを証明したが、**購入フラグ／レース前後**の運用条件を Collector 実装前に再確認すべき。

---

## 1. 検証方法

| 項目 | 内容 |
|------|------|
| 馬サンプル | `2024105886`, `2024101670`, `2024105950`, `2024106017`, `2022103522` 等（board / oikiri 由来） |
| レースサンプル | `202601010205`（札幌 5R / 2歳新馬・調教データ充足） |
| 取得 | EC2 から `urllib` + ブラウザ相当 UA（Cookie なし） |
| 非対象 | Playwright 描画依存の検証（必要時のみ JS マーカー確認） |
| 非変更 | PE / CE / AI / Prediction Logic / Research Runtime 推論 |

確認観点（要求どおり）:

1. HTML から取得可能か  
2. JavaScript 描画依存か  
3. XHR/API 経由か  
4. 取得時刻（プローブ時刻）  
5. 公開時刻（ページ上の調教日付・更新ヒント）  
6. Stable Selector を作れるか  
7. 取得成功率  

---

## 2. Source A — netkeiba Horse DB

**URL:** `https://db.netkeiba.com/horse/{horse_id}`

### 2.1 技術特性

| 観点 | 結果 |
|------|------|
| 初期 HTML | プロフィール表（調教師・馬主・生産者・セリ取引価格等）は **サーバー側 HTML に含まれる** |
| JS 描画 | 血統ブロック（`blood_table`）は **初期 HTML に無い**。ページ JS が AJAX で後挿し |
| XHR/API | `GET https://db.netkeiba.com/horse/ajax_horse_pedigree.html?id={horse_id}`（`status=OK` + HTML fragment、または HTML 直返し） |
| 既存類似 | PI は既に `ajax_horse_results.html` を使用（`horse_history.py`）。血統も同系統 |
| CloudFront | 過去に EC2→db が 400 になる事例あり。**本プローブでは 200 で成功**（UA/Referer 付き） |

### 2.2 Feature 別

#### trainer

| 項目 | 内容 |
|------|------|
| 実取得 | **成功**（例: `西園翔太 (栗東)`, `小栗実 (栗東)`） |
| 方法 | 静的 HTML: `<th>調教師</th><td>…</td>` |
| 成功率 | **5/5 (100%)** |
| 不能理由 | — |
| Stable Selector | `th:contains(調教師) + td` / regex `調教師</th>\s*<td[^>]*>(.*?)</td>` |
| 公開時刻 | 馬登録後ほぼ静的（レース週変動なし） |
| Collector | **実装可**（Phase1 で PI `trainer` 露出済みの補完／馬単位キャッシュにも可） |

#### owner

| 項目 | 内容 |
|------|------|
| 実取得 | **成功**（例: `渡邉直樹`, `吉田照哉`） |
| 方法 | 静的 HTML `<th>馬主</th>` |
| 成功率 | **5/5** |
| Collector | **実装可** |

#### breeder

| 項目 | 内容 |
|------|------|
| 実取得 | **成功**（例: `川越ファーム`, `社台ファーム`） |
| 方法 | 静的 HTML `<th>生産者</th>` |
| 成功率 | **5/5** |
| Collector | **実装可** |

#### sale_price

| 項目 | 内容 |
|------|------|
| 実取得 | **フィールドは常に存在**。値が `-` の馬が多い |
| 方法 | 静的 HTML `<th>セリ取引価格</th>` |
| 成功率 | フィールド **5/5** / 金額あり **2/5**（例: `5,720万円 (2024年 セレクトセール)`） |
| 不能理由 | 非セリ・非公開・未記載は `-`（ソース欠測でありパーサ失敗ではない） |
| Collector | **実装可**（`-` / null を正規欠損として保存） |

#### sire / damsire / pedigree

| 項目 | 内容 |
|------|------|
| 実取得 | **成功** |
| 方法 | XHR: `ajax_horse_pedigree.html?id=` → `table.blood_table` |
| 構造 | `td.b_ml[rowspan≥2]` = **父(sire)**、`td.b_fml[rowspan≥2]` = **母**、その直後の `td.b_ml` = **母父(damsire)** |
| 実測例 | `2024101670`: sire=`エフフォーリア`, damsire=`エンパイアメーカー` / `2024105886`: sire=`ブリックスアンドモルタル`, damsire=`ジャスタウェイ` |
| 成功率 | **5/5 (100%)** |
| 初期 HTML のみ | **不可**（`blood_table` 無し）。必ず AJAX か `/horse/ped/{id}/` |
| `/horse/ped/{id}/` | フルページは取得可だが表構造が異なり、本プローブの compact パーサは不安定。**Collector は AJAX を推奨** |
| JS 必須？ | ブラウザ描画は不要。**HTTP で fragment を直接取得すれば十分** |
| Collector | **実装可** |

### 2.3 Horse DB 取得時刻

| 項目 | 値 |
|------|------|
| プローブ取得時刻 | 2026-07-27（EC2、`final_probe` / `rates` 実行時） |
| ソース公開 | プロフィール・血統は通年公開（レース当日依存なし） |
| Anti-Leak | 予測生成前に取ればリークなし（静的属性） |

---

## 3. Source B — netkeiba 調教（oikiri / 一番時計 / 調子偏差値）

### 3.1 調教ページ（oikiri）

**URL:** `https://race.netkeiba.com/race/oikiri.html?race_id={race_id}&type=1`  
（`type=2/3` も HTML 返却。本証明の主対象は **type=1**）

#### 技術特性

| 観点 | 結果 |
|------|------|
| HTML | **サーバー側で調教タイム・評価まで埋め込み**（Cookie なしで取得） |
| JS 描画 | メイン表は初期 HTML。Premium ボックスは DOM 上存在するが、本サンプルではデータ本体はマスクされていない（`※※※※※※` = 0） |
| XHR | 調教タイム本体に追加 API 必須ではない |
| Stable Selector | テーブル `table.OikiriTable` / 行クラス `OikiriDataHead1` + 後続 `<tr>` の日付行 |
| 列イメージ | 日付 / コース / 馬場 / 乗り役 / **調教タイム** / 位置 / 脚色 / **評価文言** / **字母(A–E)** |

#### 調教タイム

| 項目 | 内容 |
|------|------|
| 実取得 | **成功** |
| 例 | `ジャストワナフライ` 2026/07/22(水) 札ダ → `59.7 (15.7) 44.0 (31.7) 12.3 (12.3)` |
| 成功率 | **13/14 (93%)**（1 頭は調教行なし） |
| 不能理由（1頭） | 当該馬の調教未掲載（パーサではなくソース空） |
| Collector | **実装可**（race_id 正規・type=1 固定を推奨） |

#### 調教評価

| 項目 | 内容 |
|------|------|
| 実取得 | **成功**（文言 + 字母） |
| 例 | `仕上十分` + `C` / `動き上々` + `B` / `順調` + `C` |
| 成功率 | **13/14 (93%)** |
| Collector | **実装可** |

#### 公開時刻・取得時刻

| 項目 | 内容 |
|------|------|
| 調教日付（ページ内） | 例: 2026/07/22(水), 07/15(水), 07/08(水) — 週中の追い切り記録 |
| 一般的公開 | 開催週の調教公開後（火〜木帯が中心）。**ページ上の「更新日時」専用フィールドは安定抽出せず**、行の調教日を観測時刻の根拠にする |
| プローブ取得 | 2026-07-27（レース翌日以降の HTML でも履歴行は残存） |
| Anti-Leak | **予測作成前**に snapshot すること。確定後に取っても「当時の調教」は残るが、運用は pre-race を前提にする |

#### race_id 注意

誤形式 ID（例: 日付埋め込みの `202607260305`）では **空シェル HTML（約 39KB・行 0）** になる。  
正しい netkeiba `race_id`（例: `202601010205` = 2026 / 場01 / 回01 / 日02 / R05）が必須。

---

### 3.2 一番時計

**URL:** `https://race.netkeiba.com/race/training_best_time.html?race_id={race_id}`

| 項目 | 内容 |
|------|------|
| 実取得 | **PARTIAL** |
| 無料で見えた例 | `エリカエクスプレス 63.4` / `ミッキーラヴィータ 65.5`（コース別の一部） |
| マスク | `※※※※※※` 多数 + 「スーパープレミアムコース登録で一番時計が見放題」CTA |
| 成功率 | 全コース横断の系統取得は **不可（非会員）**。無料テaser のみ |
| JS/XHR | 本体は HTML。追加 API より **課金壁**が本質 |
| Collector | **条件付き** — 無料範囲だけなら可だが Feature として不完全。課金 Cookie は本スコープ外 |

---

### 3.3 調教偏差値（調子偏差値）

**URL:** `https://race.sp.netkeiba.com/barometer/score.html?race_id={race_id}`  
（`race.netkeiba.com/barometer/...` は **404**）

| 項目 | 内容 |
|------|------|
| 実取得 | **YES（本プローブ）** |
| 方法 | 静的 HTML `Shutuba_Table` 系。列ヘッダに **「今回 偏差値」** |
| 実測例 | サトノフルーク `68 (1位)` / ノヴァヴェローチェ `57 (7位)` / ジャストワナフライ `60 (4位)` 等 **10 頭分** |
| 成功率 | **10/10**（当該レース出走頭） |
| JS | axios 等のスクリプト参照あり。ただし **偏差値数値は初期 HTML に存在**（描画待ち不要） |
| `not_purchased` | 本 HTML では `'0'`。課金状態フラグの可能性あり → **未購入セッションでの恒常性は未証明** |
| レース前後 | プローブ時は **着順付きの確定後ページ**。レース前 HTML の単独取得は未実施 |
| Collector | **実装候補 YES**。ただし実装前に (1) Cookie なしでのレース前取得 (2) `not_purchased=1` 時のマスク有無 を追加 1 レースで確認すること |

---

## 4. Feature カード（成果物要求フォーマット）

### 4.1 Horse DB

| Feature | 取得成功 | 取得方法 | 成功率 | 取得不能理由 | Research Collector 実装可 |
|---------|----------|----------|-------:|--------------|---------------------------|
| trainer | YES | HTML `th/td` | 100% (5/5) | — | YES |
| sire | YES | AJAX `blood_table` | 100% (5/5) | 初期 HTML のみでは不可 | YES |
| damsire | YES | AJAX `blood_table` | 100% (5/5) | 同上 | YES |
| breeder | YES | HTML `th/td` | 100% (5/5) | — | YES |
| owner | YES | HTML `th/td` | 100% (5/5) | — | YES |
| sale_price | PARTIAL | HTML `th/td` | フィールド100% / 金額40% | 非掲載は `-` | YES（欠損許容） |
| pedigree | YES | AJAX fragment 全体 | 100% (5/5) | — | YES（構造化 or raw） |

### 4.2 調教系

| Feature | 取得成功 | 取得方法 | 成功率 | 取得不能理由 | Research Collector 実装可 |
|---------|----------|----------|-------:|--------------|---------------------------|
| 調教タイム | YES | oikiri `type=1` HTML | 93% (13/14) | 未掲載馬 | YES |
| 一番時計 | PARTIAL | best_time HTML | 無料一部のみ | プレミアムマスク | 条件付き（課金なしでは不完全） |
| 調教評価 | YES | oikiri HTML（文言+A–E） | 93% (13/14) | 未掲載馬 | YES |
| 調教偏差値 | YES※ | barometer HTML | 100% (10/10)※ | レース前・未購入の恒常性未証 | YES（追加確認後） |

※ 確定後ページ実測。

---

## 5. Stable Selector 草案（実装時の起点）

```
# Horse profile
PROFILE_TD = r"<th[^>]*>\s*{label}\s*</th>\s*<td[^>]*>(.*?)</td>"
labels = ["調教師", "馬主", "生産者", "セリ取引価格"]

# Pedigree AJAX
GET db.netkeiba.com/horse/ajax_horse_pedigree.html?id={horse_id}
→ table.blood_table
→ sire: td.b_ml[rowspan>=2] (first)
→ dam:  td.b_fml[rowspan>=2] (first)
→ damsire: first td.b_ml after dam

# Oikiri
GET race.netkeiba.com/race/oikiri.html?race_id={id}&type=1
→ table.OikiriTable
→ horse block near OikiriDataHead1 + /horse/{id}
→ dated tr: td[0]=date, td[1]=course, td[4]=times, td[7]=eval_text, td[8]=letter

# Barometer
GET race.sp.netkeiba.com/barometer/score.html?race_id={id}
→ header contains 今回 偏差値
→ body td matching ^(\d{2,3})\s*\(
```

---

## 6. リスク・制約（実装しないが記録）

1. **db.netkeiba CloudFront 400** — 既存 PI と同じヘッダ戦略が必要。  
2. **正しい race_id** — 誤ると oikiri が空成功（HTTP 200）に見える。  
3. **一番時計** — 非会員では Feature 品質不足。  
4. **調子偏差値** — 購入フラグ / レース前の再プローブが未完。  
5. **エンコーディング** — db 系は euc-jp、race 系は utf-8 が混在。  
6. **利用規約** — 本監査は技術的取得可能性のみ。本番クローラ頻度・規約遵守は別判断。

---

## 7. 【Decision】

```
【Decision】
Action Type: Feasibility Proof Only（実装なし）
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: Low（読み取りプローブのみ）
Expected Next Action:
  1) Collector 実装するなら優先順: trainer/owner/breeder → sire/damsire → oikiri(time+eval) → sale_price
  2) 調子偏差値は「レース前・未購入」追加プローブ後に GO/NO-GO
  3) 一番時計はプレミアム方針が無い限り Backlog
  4) Prediction Logic / AI 改善は触らない
```

---

## 8. 証拠インデックス

| ファイル（EC2） | 内容 |
|-----------------|------|
| `/tmp/v101-feasibility/rates.json` | oikiri 13/14, baro 10, profile 5/5, pedigree 5/5 |
| `/tmp/v101-feasibility/extract_report.json` | セレクタ抽出 |
| `/tmp/v101-feasibility/final_probe.json` | 新鮮 fetch（pedigree AJAX・baro URL） |
| `/tmp/v101-feasibility/oikiri_type1_202601010205.html` | 調教タイム実 HTML |
| `/tmp/v101-feasibility/barometer.html` | 調子偏差値実 HTML |
| `/tmp/v101-feasibility/ped_json_*.txt` | 血統 AJAX |
| `/tmp/v101-feasibility/horse_pc_*.html` | 馬プロフィール |

**結論（短文）:** Research Collector は、Prediction Logic を変えずに、Horse DB（厩舎・馬主・生産者・父・母父・血統・セリ欄）と oikiri（調教タイム・評価）を **実 HTML/XHR から取得できる**ことが証明された。一番時計はプレミアム制限。調子偏差値は数値取得を確認済みだが、レース前・非購入条件の追証が残る。
