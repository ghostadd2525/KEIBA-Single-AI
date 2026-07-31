# Version10 Audit — Prioritization（AI改善効果基準）

**Status:** Investigation only（コード変更なし）  
**Date:** 2026-07-27  
**Scope:** V9.4 Feature 一覧を「実装しやすさ」ではなく **AI改善効果** で再順位付け  
**改善ターゲット（固定）:**

1. **2歳新馬**
2. **初出走**（本コーパスでは 2歳新馬 ≡ 初出走）
3. **Rank Degeneracy**（多重本命 / Soft−Strict ギャップ）

**根拠:**  
`docs/research/v9-younghorse-analysis.md` · `docs/research/v91-rank-degeneracy-analysis.md` · `docs/design/v91-tie-resolver.md` · `docs/audit/v94-source-feasibility-audit.md` · `docs/audit/v94-feature-matrix.csv`

**Non-goals:** Collector / PE / CE / AI推論 / Research Runtime / ResultAutomation の実装・変更

---

## 0. Verdict（先に）

| 問い | 結論 |
|------|------|
| V9.4 READY をそのまま V10 先頭にしてよいか？ | **否。** READY 5件のうち **距離・頭数・開催はタイ群内に分散せず、Resolver に寄与しない** |
| 改善の理論天井（新馬） | Soft Hit **57%**（現状 Strict **0%**）。完璧 Resolver で **最大 +4/7R** |
| 既存バンドル内シグナル | `win_prob` / 馬番は **タイ解決不能**（スコア空間も潰れている） |
| V10 で最初に実装すべき P0 | **市場 Evidence（人気・単勝・想定人気）+ 厩舎** |

**V10 P0 提案（効果優先）**

```
P0-A  win_odds + popularity + expected_popularity   ← Tie Resolver 本命
P0-B  trainer（_trainer 露出）                      ← 初出走・最短 DATA GAP
```

V9.4 READY の `jockey / frame / distance / field_size / venue` は **Collector 基盤 Wave** としては有用だが、**AI改善効果の P0 ではない**（後述 §5）。

---

## 1. 評価軸の定義

本監査は V9.4 の READY/PARTIAL/BLOCKED を破棄せず、**効果軸を主、実装を従**に再スコアする。

| 軸 | 定義 | スケール |
|----|------|----------|
| **AI改善期待** | Strict Hit / Soft回収 / 新馬 Miss 削減への期待 | High / Med / Low / None |
| **Tie Resolver寄与** | タイ集合 \|G\|≥2 から **馬を一意に分ける**能力 | High / Med / Low / **Race-level（寄与なし）** / N/A |
| **Young Horse寄与** | 2歳新馬・初出走セグメントでの情報価値 | High / Med / Low / N/A |
| **実装コスト** | V9.4 難易度 + ソース作業量 | Low / Med / High |
| **ROI** | （AI改善期待 × ターゲット適合）÷ 実装コスト | **S / A / B / C / D** |

### 1.1 ターゲット適合ルール（厳格）

| ルール | 意味 |
|--------|------|
| **R1 タイ内分散** | レース共通値（距離・開催・頭数・馬場・天候）は **Resolver に使えない** → Tie寄与 = Race-level |
| **R2 初出走定義** | `jockey_continued` は初出走で **N/A** → Young/Tie とも除外 |
| **R3 Soft天井** | Soft 外 3/7R は Resolver では回収不能。その Feature の価値は「本命群の質」側（別問題） |
| **R4 Score非改変** | Feature は Evidence / Snapshot / Resolver 入力。PE スコア改変は本優先度の対象外 |
| **R5 実証ギャップ** | 人気・オッズは **未収集のため棄却も採択もできない** — 期待は仮説だが、V9.1 が明示した最大ボトルネック |

### 1.2 効果の定量アンカー（週末 n=7）

| 指標 | 値 |
|------|-----|
| Strict Hit | 0% |
| Soft Hit / Oracle Ceiling | **57.1%** |
| Degeneracy（タイ≥3） | 71.4% |
| Soft∧¬Strict（回収候補） | **4R** |
| Soft 外 | 3R（Resolver 非対象） |
| 非新馬平均タイ | 1.17（ほぼ退化なし） |

→ **V10 の第一効果は「新馬の Soft∧¬Strict を Strict に変換すること」**。全体 Hit への波及は新馬比率に比例。

---

## 2. Feature 再評価表

凡例: V9.4 = 取得可能性。**本表の ROI は改善効果基準**（V9.4 と不一致あり得る）。

| feature | V9.4 | AI改善期待 | Tie寄与 | Young寄与 | コスト | **ROI** | 一言 |
|---------|------|------------|---------|-----------|--------|---------|------|
| **win_odds** | PARTIAL | **High** | **High** | **High** | Med | **S** | 初出走で唯一広く使える市場信号。DATA GAP が最大ボトルネック |
| **popularity** | PARTIAL | **High** | **High** | **High** | Med | **S** | 同上。タイ群内で一意化しやすい |
| **expected_popularity** | PARTIAL | **High** | **High** | **High** | Low※ | **S** | 単勝派生。単勝が揃えば即実装可 |
| **trainer** | PARTIAL | **High** | **Med–High** | **High** | **Low** | **S** | parse 済・未露出。騎手×厩舎の土台。初出走の古典情報 |
| **sire** | BLOCKED | **High** | Med | **High** | High | **A** | 過去走ゼロの事前情報。ソース未接続 |
| **damsire** | BLOCKED | **High** | Med | **High** | High | **A** | 同上（母父） |
| **horse_weight** | BLOCKED | Med | Med | **High** | High | **B** | 新馬新聞の主情報だが発表後・コレクタなし |
| **horse_weight_delta** | BLOCKED | Med | Low–Med | Med | Med–High | **B** | 体重依存 |
| **workout_rating** | BLOCKED | Med–High | Med | **High** | High | **B** | 新馬向け仮説強。評価スケール未定義 |
| **training_time** | BLOCKED | Med | Med | **High** | High | **B** | 同上 |
| **place_odds** | BLOCKED | Low–Med | Low | Low | Med | **C** | 単勝 Benchmark / 本命選定には二次。API未接続 |
| **jockey** | READY | Low–Med | Low | Low | Low | **C** | 収集容易だが新馬タイ解決の証拠なし。パース汚れ |
| **frame** | READY | Low | Low | Low | Low | **D** | V9.1: soft回収 **0/4**。弱仮説 |
| **track_condition** | PARTIAL | Low | **Race-level** | Low | Low | **D** | タイ内非分散。going は当日変動 |
| **weather** | PARTIAL | Low | **Race-level** | Low | Low | **D** | 同上 |
| **moisture_rate** | BLOCKED | Low | **Race-level** | Low | High | **D** | ソースなし・タイ非寄与 |
| **distance** | READY | Low※ | **Race-level** | Low※ | Low | **D†** | Resolver 無効。Mining 文脈のみ |
| **field_size** | READY | Low※ | **Race-level** | Low※ | Low | **D†** | 同上 |
| **venue** | READY | Low※ | **Race-level** | Low※ | Low | **D†** | 同上 |
| **jockey_continued** | PARTIAL | — | **N/A** | **N/A（初出走）** | Low | **—** | ターゲット外（3歳未勝利再検証用） |
| **surface**（馬場の安定成分） | （track 内） | Low | **Race-level** | Low | Low | **D†** | レース共通 |

※ expected_popularity のコスト Low は「単勝経路が揃った後」。単勝自体は Med。  
※ distance/field_size/venue の「Low※」= クラス別 Mining・層別には使えるが、**本ターゲット（退化解決）では効果なし**。  
† V9.4 Wave0 READY でも **改善ROIは D**。

---

## 3. 軸別ディープダイブ

### 3.1 Tie Resolver 寄与

```
高寄与（タイ内で馬を分離しうる）
  popularity / win_odds / expected_popularity
  trainer / sire / damsire
  horse_weight* / workout* / training_time*
  jockey（弱）/ frame（実証 0）

寄与なし（レース共通値）
  distance / field_size / venue / weather / going / moisture

定義不能
  jockey_continued（初出走）
```

V9.1 スコアカード実測:

| 候補 | soft回収 |
|------|----------:|
| baseline 馬番 | 0/4 |
| win_prob | 0/4（値同一） |
| frame | 0/4 |
| 人気・オッズ・厩舎・血統・調教・体重 | **未検証（DATA GAP）** |

→ **未検証のまま放置している市場・厩舎が、効果面の最優先ギャップ。**

### 3.2 Young Horse / 初出走寄与

| 情報族 | なぜ効くか（仮説） | 証拠状態 |
|--------|-------------------|----------|
| **市場** | 過去走ゼロでも市場が事前情報を集約 | DATA GAP（0% filled） |
| **厩舎** | 新馬成績・仕上がりの代理 | parse 済・未露出 |
| **血統** | 距離・芝ダ適性の事前 | 未収集 |
| **調教・体重** | 仕上がり・気配 | 未収集・発表依存 |
| **継続騎乗** | 初出走では定義不能 | N/A |
| **レースメタ** | 全頭共通 → 相対順位に使えない | READY だが効果薄 |

主メカニズムは **情報欠落そのものではなく Rank Degeneracy**（Soft 57%）。  
よって Young 改善の最短経路は「新特徴で PE を再学習」ではなく **タイ集合上の Evidence Resolver**。

### 3.3 AI改善期待の定量イメージ（仮説・上限）

| シナリオ | 新馬 Strict（n=7 上限感） | 全体への波及感（51R） |
|----------|---------------------------|----------------------|
| 現状 | 0% | 全体 Hit 15.7% |
| Soft 内完璧解決 | **57%**（+4R） | 約 +7.8pt（4/51） |
| Soft 外も改善（別手段） | >57% | 要候補プール研究 |
| READY Wave0 のみ Snapshot 化 | **≈0pt（Resolver未接続）** | Collector 基盤のみ |

**重要:** Feature を Snapshot に載せるだけでは Strict は上がらない。  
**Resolver（または同等の選定ポリシー）が消費者**として接続されて初めて改善になる。  
V10 の「実装」定義は **Evidence 収集 + Resolver 採用可能性の検証**までを含む（PE 非改変）。

---

## 4. V9.4 との差分（なぜ順位が変わるか）

| V9.4 結論 | V10 再評価 |
|-----------|------------|
| Collector は READY 5件から | READY 5件は **取得容易**だが、うち3件は **タイ非寄与** |
| PARTIAL は先送り | 市場・厩舎は **効果上 P0**（取得経路はある／露出のみ） |
| BLOCKED は後回し | 血統は **効果 A**だがコスト High → P1（効果枠） |
| 実装しやすさ = 優先 | **AI改善効果 × ターゲット適合 = 優先** |

```
V9.4 優先イメージ:  jockey, frame, distance, field_size, venue
V10 優先イメージ:  win_odds, popularity, expected_popularity, trainer
                   → (P1) sire, damsire
                   → (基盤) READY メタは Snapshot 配管として並行可
```

---

## 5. Version10 実装提案（効果順）

### 5.1 P0（最初に実装すべき）

#### P0-A — Market Evidence Bundle（単勝系）

| ID | Feature | 役割 |
|----|---------|------|
| F1 | `win_odds` | Resolver 主信号 |
| F2 | `popularity` | Resolver 主信号（一意化しやすい） |
| F3 | `expected_popularity` | 単勝ソート派生。欠測時フォールバック設計 |

**なぜ P0 か**

- 初出走で過去走・継続騎乗が使えないときの **唯一の広域市場情報**
- Soft∧¬Strict 4R の回収仮説が最も自然
- V9.1 / V9.4 双方が「最大 DATA GAP / 経路はあるが空」と一致

**前提作業（効果のための取得）**

- race_refresh 経路への JRA `type=1` マージ（または board と同一ソースの Snapshot）
- `observed_at ≤ prediction_created_at`（Anti-leak）
- Missing 時は Resolver unresolved（Fail-Open）

**成功条件（Research）**

- 新馬タイ群で人気/オッズが **一意トップを返し**、Soft∧¬Strict の回収率を測定
- 回収 0 なら仮説棄却（実装しやすさで押し切らない）

#### P0-B — Trainer Exposure（厩舎）

| ID | Feature | 役割 |
|----|---------|------|
| F4 | `trainer` | タイ内カテゴリ信号 / 騎手×厩舎の土台 |

**なぜ P0 か**

- Young / 初出走の古典情報
- **実装コスト最低帯**（`_trainer` 露出）なのに V9.4 で PARTIAL のまま
- 市場と直交する Evidence（市場が未発売の早朝 Snapshot でも使える可能性）

**成功条件**

- タイ群内で厩舎が一意に分かれる頻度
- 単独正解率（市場と独立・交差）

### 5.2 P1（効果は高いがソース作業が重い）

| Feature | 理由 |
|---------|------|
| `sire` / `damsire` | 初出走の事前情報として High。Collector 新規 → コスト High |
| （任意）`horse_weight*` / `workout*` | 新馬新聞系。発表タイミング・スケール定義が先行 |

P1 は P0 の **回収実証後**に着手（Soft 外 3R や市場無効時の代替）。

### 5.3 P2 / 非優先（本ターゲットでは ROI 低）

| Feature | 理由 |
|---------|------|
| `frame` | 実証 soft回収 0 |
| `distance` / `field_size` / `venue` / `weather` / `going` / `moisture` | Race-level |
| `place_odds` | 単勝選定の二次；API 未接続 |
| `jockey_continued` | 初出走 N/A |
| `jockey` 単独 | 証拠不足・ノイズ |

※ READY メタを Snapshot に載せる **配管作業**は、P0 と並行してよい（コスト低・将来 Mining 用）。  
ただし **「V10 最初の AI改善チケット」の Definition of Done にしてはならない。**

---

## 6. 推奨ロードマップ（効果ゲート付き）

```
Wave V10.0  Evidence P0
  ├─ trainer 露出 → Snapshot
  ├─ win_odds / popularity 取得経路修正 + Snapshot
  └─ expected_popularity 派生
        │
        ▼  Research Gate G1
     新馬タイ群で soft回収率を測定
        │
        ├─ 回収あり → Tie Resolver 設計を本番候補化（別承認・Score非改変）
        └─ 回収なし → 仮説棄却。P1 血統へ（PE 改変は依然 Lock）

Wave V10.1  Pedigree P1（sire/damsire）
Wave V10.2  Workout / Weight（発表後ウィンドウ）
Wave 並行    READY メタの Snapshot 配管（効果ゲート対象外）
```

**Gate G1 を飛ばして Resolver を本番化しない**（Evidence-First: V9.1 設計原則）。

---

## 7. ROI ランキング（トップ）

| Rank | Feature | ROI | V10 扱い |
|-----:|---------|-----|----------|
| 1 | win_odds | **S** | **P0-A** |
| 1 | popularity | **S** | **P0-A** |
| 1 | expected_popularity | **S** | **P0-A** |
| 1 | trainer | **S** | **P0-B** |
| 5 | sire | **A** | P1 |
| 5 | damsire | **A** | P1 |
| 7 | workout_rating / training_time / horse_weight* | **B** | P2候補 |
| — | place_odds / jockey | **C** | 非優先 |
| — | frame / race-level READY | **D** | 配管のみ可 |

---

## 8. リスク・限界

1. **n=7** — 効果サイズの仮説。G1 で複数週末再現が必須。  
2. 市場 Feature は **発売前 Snapshot では Missing** — 予測時刻設計が ROI を左右する。  
3. Soft 外 3R は P0 Resolver では救えない。  
4. Snapshot Store / Collector 自体は未実装（V9.2–9.3 設計）。P0 は「取得可能性修正 + 研究用永続化」が前提。  
5. 本監査は **優先順位のみ**。実装チケット化しても PE/CE/AI/RA は Hard Lock。

---

## 9. 成果物チェック

| 成果物 | 内容 |
|--------|------|
| 本ファイル | 効果基準の再優先度・P0 提案 |
| （参照）V9.4 matrix | 取得可能性の正本は維持。本票が効果正本 |

---

## 10. 変更境界

| 領域 | 本監査 |
|------|--------|
| コード | **未変更** |
| Feature / Collector 実装 | **なし** |
| PE / CE / AI推論 / Research Runtime / RA | **未変更** |

---

## 11. 参照

- `docs/research/v9-younghorse-analysis.md`  
- `docs/research/v91-rank-degeneracy-analysis.md`  
- `docs/design/v91-tie-resolver.md`  
- `docs/design/v93-feature-catalog.md`  
- `docs/audit/v94-source-feasibility-audit.md`  
- `docs/audit/v94-feature-matrix.csv`
