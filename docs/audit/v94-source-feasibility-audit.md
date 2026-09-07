# Version9.4 Audit — Source Feasibility（Prediction Snapshot）

**Status:** Investigation only（コード変更なし）  
**Date:** 2026-07-27  
**Scope:** V9.2 Snapshot / V9.3 Feature Catalog の「実際に取得できるか」  
**Matrix:** `docs/audit/v94-feature-matrix.csv`  
**Non-goals:** Collector 実装 / Feature 追加 / PE・CE・AI・RA・Research Runtime 変更

---

## 0. 判定サマリ

| Verdict | 件数 | Feature |
|---------|-----:|---------|
| **READY** | **5** | 騎手 / 枠 / 距離 / 頭数 / 開催 |
| **PARTIAL** | **7** | 人気 / 想定人気 / 単勝 / 継続騎乗 / 厩舎 / 馬場 / 天候 |
| **BLOCKED** | **8** | 複勝 / 父 / 母父 / 馬体重 / 馬体重増減 / 追切 / 調教時計 / 含水率 |

CSV 全 20 行（`v94-feature-matrix.csv`）。

**Collector 実装対象（本監査の結論）:** **READY のみ**（5 Feature）。  
PARTIAL / BLOCKED は理由付きで先送り（露出・API・新規パーサが必要）。

### 横断事実

1. **Prediction Snapshot Store 自体は未実装**（設計のみ）。本監査は「現行 PI/DB/CSV に同値が既にあるか」。  
2. `runners.csv` に載るものでも、**人気・単勝は実測で空埋めが多い**（V9.1: 新馬 refresh 経路 0%）。  
3. **厩舎は HTML で既に parse（`_trainer`）されているが CSV 未露出** — 最短の PARTIAL→READY 候補。  
4. JRA odds API は **`type=1`（単勝）のみ** — 複勝は BLOCKED。

---

## 1. 監査方法

| 観点 | 根拠 |
|------|------|
| コード | `parse.py`, `race_refresh.py`, `horse_history.py`, `client.py`（odds）, `service.py`（board） |
| スキーマ | AI DB `entries` / `races` / `predictions` |
| 実測 | `docs/research/v91-rank-degeneracy-analysis.md`（人気・オッズ 0%） |
| 設計 | `v92-prediction-snapshot.md`, `v93-feature-catalog.md` |

判定基準:

| Verdict | 定義 |
|---------|------|
| **READY** | 予測時点で既存 Collector/CSV/DB から安定取得できる。Research Collector が読んで Snapshot 化できる |
| **PARTIAL** | ソースまたは中間データはあるが、経路欠落・時刻依存・未派生・品質問題でそのままでは不十分 |
| **BLOCKED** | 予測時点 Collector に必要なソース／アダプタが無い、または発表前で実質使えない |

---

## 2. Feature 一覧（①〜⑨ + Verdict）

凡例: 取得済み = 現行永続化（runners/DB 等）に載っているか。Snapshot 専用ストアは全 NO。

### 2.1 READY（Collector 実装対象）

| Feature | ①取得済 | ②取得元 | ③Pred時点 | ④タイミング | ⑤方法 | ⑥失敗理由 | ⑦Missing | ⑧価値 | ⑨難易度 |
|---------|---------|---------|-----------|-------------|-------|-----------|----------|-------|---------|
| **騎手** | YES | Netkeiba | YES | 枠出〜当日 | HTML→CSV | パース汚れ | Low | P0 | Low |
| **枠** | YES | Netkeiba | YES | 枠順確定後 | HTML→CSV | 未確定時 0 | Low | P0 | Low |
| **距離** | YES | Netkeiba / 既存DB | YES | カード公開後 | HTML→CSV/DB | パース失敗 | Low | P0 | Low |
| **頭数** | YES | Netkeiba / 既存DB | YES | カード公開後 | 派生/DB | 取消ズレ | Low | P0 | Low |
| **開催** | YES | Netkeiba / 既存DB | YES | 開催確定後 | HTML→CSV/DB | 命名差 | Low | P0 | Low |

**READY の実装イメージ（設計のみ）:** Research Collector が既存 `runners.csv` / `races` を読み、`prediction_id` に紐づけて Snapshot へコピー。AI 変更不要。

---

### 2.2 PARTIAL（理由明記・実装対象外）

| Feature | ① | ② | ③ | ④ | ⑤ | ⑥主な理由 | ⑦ | ⑧ | ⑨ | PARTIAL 理由 |
|---------|----|----|----|----|----|-----------|----|----|----|----------------|
| **人気** | NO※ | Netkeiba+JRA | PARTIAL | 発売後〜締切前 | API+HTML（列あり） | 未発表・refresh 未マージ | High | P0 | Medium | 経路はあるが予測生成時に空。board と refresh 不一致 |
| **単勝オッズ** | NO※ | Netkeiba+JRA | PARTIAL | 同上 | API+HTML | 同上 | High | P0 | Medium | 同上。JRA `type=1` は board で使用可 |
| **想定人気** | NO | 派生 | PARTIAL | 単勝取得後 | 未実装 | 単勝欠損 | High | P0 | Low | 単勝が揃えば Low で実装可。単勝が PARTIAL のため連動 |
| **継続騎乗** | NO | Netkeiba | PARTIAL | history 取得時 | 未実装（入力あり） | 新馬 N/A・週末 skip | Medium | P0 | Low | `jockey_today`+`history_jockey` あり。派生のみ不足 |
| **厩舎** | NO | Netkeiba | PARTIAL | 枠出〜当日 | HTMLのみ | CSV 未露出 | High | P0 | Low | `_trainer` parse 済。**露出すれば READY 化** |
| **馬場** | YES | Netkeiba | PARTIAL | 前日〜当日 | HTML→CSV | going 未知 | Medium | P0 | Low | surface（芝/ダ）は安定。良/稍重は当日変動 |
| **天候** | YES | Netkeiba | PARTIAL | 当日朝〜 | HTML→CSV | unknown | Medium | P0 | Low | 列はあるが早朝 Snapshot では欠測多い |

※ runners に列はあるが実測充足が低く「運用上未取得」とみなす。

---

### 2.3 BLOCKED（理由明記・実装対象外）

| Feature | ① | ② | ③ | ④ | ⑤ | ⑥主な理由 | ⑦ | ⑧ | ⑨ | BLOCKED 理由 |
|---------|----|----|----|----|----|-----------|----|----|----|----------------|
| **複勝オッズ** | NO | JRA（想定） | NO | 発売後 | 未実装 | API type=2 未接続 | High | P0 | Medium | 単勝 API のみ。複勝アダプタなし |
| **父** | NO | Netkeiba（想定） | NO | 静的だが未収集 | 未実装 | ページ未接続 | High | P1 | High | pedigree コレクタなし |
| **母父** | NO | Netkeiba（想定） | NO | 同上 | 未実装 | 同上 | High | P1 | High | 同上 |
| **馬体重** | NO | Netkeiba（想定） | PARTIAL→実質 NO | **発表後** | 未実装 | 未発表・当日パーサなし | High | P1 | High | 斤量と混同注意。当日ボードなし |
| **馬体重増減** | NO | Netkeiba（想定） | NO | 発表後 | 未実装 | 同上 | High | P1 | Medium | 当日コレクタ依存 |
| **追切** | NO | Netkeiba（想定） | NO | 調教公開後 | 未実装 | ページなし | High | P2 | High | 評価スケール未定義 |
| **調教時計** | NO | Netkeiba（想定） | NO | 同上 | 未実装 | ページなし | High | P2 | High | 同上 |
| **含水率** | NO | JRA/開催 | NO | 当日計測後 | 未実装 | 取得不可・開催差 | High | P2 | High | ソース未接続。null 正規可（設計） |

---

## 3. 追加分類

### 3.1 Netkeiba だけで取得できるもの（理論含む）

| 分類 | Feature |
|------|---------|
| **既に Netkeiba→CSV/DB** | 騎手, 枠, 距離, 頭数, 開催, 馬場(surface), 天候 |
| **Netkeiba HTML に存在・未露出/未派生** | 厩舎(`_trainer`), 継続騎乗(入力のみ), 人気/単勝(shutuba 埋め込み・不安定) |
| **Netkeiba にページはあるが未実装** | 父, 母父, 追切, 調教時計, 当日馬体重 |

### 3.2 JRA 等の別ソースが必要なもの

| Feature | ソース |
|---------|--------|
| 単勝オッズ（安定取得） | JRA odds API `type=1`（PI board で使用中） |
| 複勝オッズ | JRA odds API place（**未接続**） |
| 人気（安定） | JRA 単勝ペイロード内 popularity または公式人気 |
| 含水率 | JRA / 開催当日情報（**未接続**） |

### 3.3 Prediction 時点では取得できない／極めて不安定なもの

| Feature | 理由 |
|---------|------|
| 馬体重 / 増減 | **馬体重発表前**は正規 Missing。発表後もコレクタなし |
| 良/稍重（馬場状態）・天候 | 当日更新。早朝予測では `unknown` |
| 複勝・追切・調教・含水・血統 | ソース未接続 |
| 継続騎乗（新馬） | 定義不能（`not_applicable`） |
| 人気・単勝（発売前） | 未発表 |

---

## 4. Collector 実装スコープ勧告（監査結論）

### Wave 0（本監査の READY のみ）

```
jockey, frame, distance, field_size, venue
(+ surface を馬場の安定成分として任意併記可)
```

- 既存 `runners.csv` / `races` 読取のみ  
- AI / PE 変更不要  
- Anti-leak: カード系は予測作成前に確定している前提で `observed_at ≈ shutuba_fetch_time`

### Wave 1（PARTIAL → READY 化の前提作業・本票では実装しない）

| 作業 | 効果 |
|------|------|
| `_trainer` を runners へ露出 | 厩舎 → READY |
| race_refresh に JRA 単勝マージ + observed_at | 人気・単勝 → READY 候補 |
| `expected_popularity` 派生 | 想定人気 → READY（単勝依存） |
| `jockey_continued` 派生 | 継続騎乗 → READY（新馬は null） |

### Wave 2+（BLOCKED 解除）

複勝 API、血統、当日馬体重、調教、含水率 — いずれも **新規ソース作業**。Collector 本体より先にソースアダプタ設計が必要。

---

## 5. リスク・注意

1. **斤量 ≠ 馬体重** — `weight_carried` を馬体重に流用しない。  
2. **frame=0** — Missing 扱い必須（READY でも品質ルール要）。  
3. **週末 history skip** — 継続騎乗の Missing が週末に跳ねる。  
4. **Snapshot Store 未存在** — READY Feature も「コピー先」が無い。V9.3 Collector 実装時に Store が前提。  
5. 本監査は **取得可能性** のみ。Tie Resolver 有効性は別（V9.1）。

---

## 6. 成果物チェック

| 成果物 | 内容 |
|--------|------|
| 本ファイル | 判定・分類・勧告 |
| `docs/audit/v94-feature-matrix.csv` | ①〜⑨ + verdict 機械可読 |

---

## 7. 変更境界

| 領域 | 本監査 |
|------|--------|
| コード | **未変更** |
| Collector 実装 | **なし** |
| Feature 追加 | **なし** |
| AI / PE / CE / RA / Research Runtime | **未変更** |

---

## 8. 参照

- `docs/design/v92-prediction-snapshot.md`  
- `docs/design/v93-feature-catalog.md`  
- `docs/design/v93-research-collector.md`  
- `docs/research/v91-rank-degeneracy-analysis.md`  
- `services/pi-keibanet-api/pi_keibanet/netkeiba/parse.py`（`_trainer`, odds parse）  
- `services/pi-keibanet-api/pi_keibanet/netkeiba/client.py`（`type=1` only）
