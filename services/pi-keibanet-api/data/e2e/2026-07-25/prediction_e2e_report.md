# E2E Prediction + Web API 最終検証 (2026-07-25)

## 1. Prediction 実行結果

### 新潟6R

- race_id: `2026-07-25-01-06`
- race_name: 豊栄特別
- Prediction: **OK**
- FeatureLoader: OK
- evaluate(): OK
- Candidate Evaluation: OK
- Entries: 18
- Candidates: 18件
- Confidence: 5.5%

Top5:

1位 4番 コルドンブルー (Confidence 9.8%)
2位 7番 シャンソンドール (Confidence 9.3%)
3位 13番 ホウオウタイタン (Confidence 5.5%)
4位 9番 ソニックライン (Confidence 5.3%)
5位 17番 リカントロポ (Confidence 5.3%)

### 新潟7R

- race_id: `2026-07-25-01-07`
- race_name: 新潟日報賞
- Prediction: **OK**
- FeatureLoader: OK
- evaluate(): OK
- Candidate Evaluation: OK
- Entries: 18
- Candidates: 18件
- Confidence: 3.8%

Top5:

1位 7番 コートアリシアン (Confidence 6.6%)
2位 3番 ウナギノボリ (Confidence 5.7%)
3位 4番 エイムフォーエース (Confidence 5.6%)
4位 14番 ボンヌソワレ (Confidence 5.6%)
5位 9番 スマイルアップ (Confidence 5.6%)

### 新潟8R

- race_id: `2026-07-25-01-08`
- race_name: 清津峡特別
- Prediction: **OK**
- FeatureLoader: OK
- evaluate(): OK
- Candidate Evaluation: OK
- Entries: 14
- Candidates: 14件
- Confidence: 5.3%

Top5:

1位 2番 イリュストル (Confidence 9.3%)
2位 9番 バッカステソーロ (Confidence 8.6%)
3位 4番 ヴィエントデコラ (Confidence 7.8%)
4位 5番 ケルピー (Confidence 7.7%)
5位 14番 ロケットパンチ (Confidence 7.5%)

### 中京6R

- race_id: `2026-07-25-02-06`
- race_name: 四日市特別
- Prediction: **OK**
- FeatureLoader: OK
- evaluate(): OK
- Candidate Evaluation: OK
- Entries: 22
- Candidates: 22件
- Confidence: 4.9%

Top5:

1位 10番 ゼロヴィジビリティ (Confidence 8.0%)
2位 15番 ヘリテージブルーム (Confidence 6.2%)
3位 6番 ザックザク (Confidence 5.8%)
4位 1番 アリエスキング (Confidence 5.0%)
5位 3番 エブリーポッシブル (Confidence 4.9%)

### 中京7R

- race_id: `2026-07-25-02-07`
- race_name: 関ケ原S
- Prediction: **OK**
- FeatureLoader: OK
- evaluate(): OK
- Candidate Evaluation: OK
- Entries: 11
- Candidates: 11件
- Confidence: 6.9%

Top5:

1位 9番 ミュージシャン (Confidence 12.1%)
2位 11番 リンフレスカンテ (Confidence 10.9%)
3位 8番 ミッキーゴールド (Confidence 9.2%)
4位 5番 タイセイフェリーク (Confidence 8.7%)
5位 7番 ハーツコンチェルト (Confidence 8.6%)

### 中京8R

- race_id: `2026-07-25-02-08`
- race_name: 香嵐渓特別
- Prediction: **OK**
- FeatureLoader: OK
- evaluate(): OK
- Candidate Evaluation: OK
- Entries: 13
- Candidates: 13件
- Confidence: 7.6%

Top5:

1位 10番 ブラックシャリマー (Confidence 12.4%)
2位 3番 キシダンチョウ (Confidence 9.3%)
3位 12番 メイショウナルカミ (Confidence 8.7%)
4位 5番 サイモンシャリオ (Confidence 7.3%)
5位 6番 サラコスティ (Confidence 7.3%)

### 札幌10R

- race_id: `2026-07-25-03-10`
- race_name: ライラック賞
- Prediction: **OK**
- FeatureLoader: OK
- evaluate(): OK
- Candidate Evaluation: OK
- Entries: 11
- Candidates: 11件
- Confidence: 7.9%

Top5:

1位 3番 ウェイクフィールド (Confidence 13.1%)
2位 8番 ライフセービング (Confidence 10.3%)
3位 6番 バースライト (Confidence 8.9%)
4位 1番 アスクデッドヒート (Confidence 8.8%)
5位 4番 ジュンツバメガエシ (Confidence 8.7%)

### 札幌11R

- race_id: `2026-07-25-03-11`
- race_name: TVh賞
- Prediction: **OK**
- FeatureLoader: OK
- evaluate(): OK
- Candidate Evaluation: OK
- Entries: 12
- Candidates: 12件
- Confidence: 9.0%

Top5:

1位 12番 ロジケープ (Confidence 13.8%)
2位 1番 アスクケンタッキー (Confidence 8.3%)
3位 2番 アンジュプロミス (Confidence 8.1%)
4位 10番 メルトユアハート (Confidence 7.9%)
5位 7番 サウスバンク (Confidence 7.8%)

### 札幌12R

- race_id: `2026-07-25-03-12`
- race_name: 桑園特別
- Prediction: **OK**
- FeatureLoader: OK
- evaluate(): OK
- Candidate Evaluation: OK
- Entries: 14
- Candidates: 14件
- Confidence: 8.4%

Top5:

1位 5番 セボンサデッセ (Confidence 13.9%)
2位 10番 ベラジオワールド (Confidence 11.0%)
3位 6番 ハイクオリティ (Confidence 6.5%)
4位 8番 フェスタリア (Confidence 6.4%)
5位 9番 フォーワンセルフ (Confidence 6.4%)

## 2. 妥当性チェック

- Candidate 0件: 0
- evaluate 失敗: 0
- Confidence 欠損: 0
- Rank 欠損: 0
- 空結果: 0

## 3. Web API レース一覧

GET `/v1/races?date=2026-07-25` → count=9

### 新潟

- 新潟6R | race_id=`2026-07-25-01-06` | name=豊栄特別
- 新潟7R | race_id=`2026-07-25-01-07` | name=新潟日報賞
- 新潟8R | race_id=`2026-07-25-01-08` | name=清津峡特別

### 中京

- 中京6R | race_id=`2026-07-25-02-06` | name=四日市特別
- 中京7R | race_id=`2026-07-25-02-07` | name=関ケ原S
- 中京8R | race_id=`2026-07-25-02-08` | name=香嵐渓特別

### 札幌

- 札幌10R | race_id=`2026-07-25-03-10` | name=ライラック賞
- 札幌11R | race_id=`2026-07-25-03-11` | name=TVh賞
- 札幌12R | race_id=`2026-07-25-03-12` | name=桑園特別

## 最終報告

- Prediction成功レース数: **9** / 9
- Prediction失敗レース数: **0**
- 推奨馬が正常出力されたレース数: **9**
- Web APIで利用可能なレース数: **9**

### Web公開に向けて残る課題

- オッズ未確定時（shutuba `---.-`）は PI 再取得で odds/popularity が空になる場合がある
- Collector 形式 race_id と Win5 形式 race_id が併存（Web は Win5 `race_id` を推奨）
- `/v1/predictions` は FeatureLoader の daily CSV / DB に依存（当日 features 生成が前提）
- 未公開レース（1R〜5R 等）は一覧に出さない（意図的）。公開後に自動追加される
