# Version46 — Stage Design

**Date:** 2026-07-28  
**Parent:** `v46-migration-plan.md`  
**Type:** Design only

各 Stage について: 目的 / 依存 / 作業範囲（設計） / 影響 / Rollback / PASS。

---

## S0 — Baseline Freeze

### Purpose
移行契約の固定。現行 Production Trigger を「Legacy Path」、V44 を「Target Spec」として宣言する。

### Depends on
V43 / V44 / V45 文書の受理。

### Scope（設計）
- Legacy: `classify_world_line_type` / `TRIGGER_RULES` R1–R8 を変更禁止ベースラインに記録
- Target: V44 Logic Form / Must / Aux / Forbidden / Evaluation Order
- Gap: V45 Compliance 表を初期 KPI

### Production Decision
**変更なし**

### Rollback Point
なし（文書ロックのみ）。S0 取消 = 移行プロジェクト中止。

### PASS
- [ ] Legacy / Target / Gap の三文書が Governance で「移行正本」指定される
- [ ] 以降 Stage が Legacy を無断変更しないことが宣言される

---

## S1 — Shadow Dual-Eval

### Purpose
同一レース入力に対し Legacy 決定と V44 Logic Form 評価を **並列観測**する（決定は Legacy のまま）。

### Depends on
S0 PASS

### Scope（設計）
- Research / Shadow 層でのみ Dual-Eval
- 出力: per-race Legacy world / Spec MATCH set / Must 欠落 / Forbidden 抵触 / 不一致理由
- Production の return 値は触らない

### Production Decision
**変更なし**

### Rollback Point
Shadow ジョブ停止。Production 挙動不変のためデータ破棄で足りる。

### PASS
- [ ] N レース以上で Dual-Eval が再現可能に完走（N は運用が定義）
- [ ] Legacy 決定分布が Dual-Eval 導入前後で一致（決定非干渉の証明）
- [ ] V45 項目①–⑦相当の Shadow 差分レポートが自動生成される

---

## S2 — Must Signal Readiness

### Purpose
V44 Must 概念ごとに「供給可能か / 欠落か / 別名のみか」をゲートする。  
**Signal 生成の実装は本 Stage の必須成果ではない**（別承認）。Readiness 判定のみ。

### Depends on
S1 PASS（欠落が Shadow で定量化されていること）

### Scope（設計）
Must カタログ（V44）:

| Must 概念 | Readiness 判定対象 |
|---|---|
| top_gap↑/↓ | `get_context_top_gap` 等の **既存関数の観測可能性** |
| ability_separation | top1/top2/median 系の観測可能性 |
| upper_ability_band | 定義可能性（既存特徴の組合せ可否） |
| aptitude_fit | 定義可能性 |
| mid_eval_band_open / top_monopoly↓ | 定義可能性 |
| multi_path_active | Shadow 上の複数 MATCH 競合として定義可能か |
| exception_flag | 明示フラグの有無（無ければ Ready=No） |

状態: `Ready` / `Proxy-only` / `Missing`

### Production Decision
**変更なし**

### Rollback Point
Readiness 台帳の改訂差戻し。コード変更が無い前提。

### PASS
- [ ] 全 Must に Ready / Proxy-only / Missing が付与される
- [ ] Missing がある World は S4 当該 World を **Blocked** と明示
- [ ] Proxy-only は S3 で「仕様上許容する近似」か「禁止」か判定待ちリストに載る

---

## S3 — Threshold / Polarity ADR

### Purpose
V44 は閾値なし仕様。Production 移行には極性判定の **運用契約（ADR）** が必要。  
本 Stage は ADR 作成ゲート。**数値の Production 書き込みは後続実装承認。**

### Depends on
S2 PASS

### Scope（設計）
- Polarity 判定の原則（相対順位 / 分布分位 / 絶対閾値のどれを許すか）
- World 境界の Exclusion 評価順
- 「Proxy-only Must」の扱い（禁止なら S2 Missing 扱いへ戻す）

### Production Decision
**変更なし**（ADR のみ）

### Rollback Point
ADR を Draft に戻す / Reject。S2 台帳は維持。

### PASS
- [ ] ADR Accepted（または明示 Reject → 移行停止）
- [ ] S4 で使う適合判定ルールが文書化される
- [ ] 数値表を持つ場合でも「実装コミット」とは分離して管理される

---

## S4 — Per-World Shadow Compliance

### Purpose
World 単位で Shadow 適合を上げる検証。推奨順は V45 Compliance 降順（破壊小→大）。

### Depends on
S3 PASS

### Recommended sequence

| Sub-stage | World | V45 Compliance | 根拠 |
|---|---|---:|---|
| S4.1 | rank7 | 64% | 最短ギャップ |
| S4.2 | bug | 50% | 次点。exception Must の Readiness 依存 |
| S4.3 | mixed | 36% | multi_path 定義が S5 と隣接 |
| S4.4 | midupper | 36% | 3 Must 軸 |
| S4.5 | midhole | 36% | Aux 昇格の解消が必要 |
| S4.6 | core | 0% | 最大破壊。S5/S6/S7 と直結 |

### Scope（設計）
- 各 Sub-stage: Shadow 上で V44 Logic Form の MATCH 率・Forbidden 抵触率・Legacy 差分を計測
- Production Legacy Path は維持

### Production Decision
**変更なし**

### Rollback Point
当該 Sub-stage の Shadow プロファイルを無効化。前 Sub-stage のプロファイルに戻す。

### PASS（各 Sub-stage）
- [ ] 当該 World の Shadow Compliance（V45 同 ①–⑦）が Stage 目標を満たす
- [ ] Forbidden 抵触率がゲート以下
- [ ] Missing Must が残る場合は **Blocked** で次へ進まない（特に S4.6）

---

## S5 — Unsatisfied Semantics Shadow

### Purpose
V44: 全 World Must 未充足 ⇒ *unsatisfied*（silent core 禁止）を Shadow で検証。

### Depends on
S4（S4.1–S4.5 推奨 PASS。S4.6 は S5 と同時設計可だが Cutover は S7）

### Scope（設計）
- Shadow 出力に `unsatisfied` を導入
- Legacy が core だったケースのうち Spec が unsatisfied の比率を報告
- mixed（複数 MATCH）と unsatisfied（0 MATCH）の分離を確認

### Production Decision
**変更なし**

### Rollback Point
Shadow の unsatisfied ラベルをオフ。Legacy 比較継続。

### PASS
- [ ] 0 MATCH ⇒ unsatisfied が Shadow で一貫
- [ ] ≥2 MATCH ⇒ mixed 仕様と矛盾しない
- [ ] unsatisfied を core に再マップする Hidden Rule が Shadow に存在しない

---

## S6 — Flagged Soft Cutover

### Purpose
限定環境（research / canary / flag）でのみ決定経路を V44 側へ切替。

### Depends on
S5 PASS、S4 で Cutover 対象 World が Unblocked

### Scope（設計）
- Feature Flag: `world_trigger_path = legacy | v44_shadow_decide`
- 既定は legacy
- 対象環境・対象レース範囲を制限
- Prediction / PE / CE の契約変更は **しない**（World ラベル供給元のみ切替）

### Production Decision
**限定 Yes**（フラグ ON 環境のみ）

### Rollback Point
**Flag → legacy（即時）**  
これが本計画の主 Rollback Point。

### PASS
- [ ] Flag OFF で Legacy とビット一致
- [ ] Flag ON 限定範囲で障害率・不一致率がゲート内
- [ ] Rollback 訓練（Flag 戻し）が記録される
- [ ] PE/CE/Prediction の入出力契約が意図せず変わっていないことの確認

---

## S7 — DEFAULT Removal Cutover

### Purpose
core の DEFAULT 残余を廃止し、Positive Match + unsatisfied を本番既定にする。

### Depends on
S6 PASS、S4.6（core）Shadow PASS、S2 で core Must が Ready（または ADR 許容 Proxy）

### Scope（設計）
- Legacy `else → core_world` を廃止する設計切替
- unsatisfied の正式な下流扱い（ログ / スキップ / 安全側）を文書化  
  ※ 下流 PE 変更は S8。S7 では「World 決定層」の契約まで

### Production Decision
**Yes（本切替）**

### Rollback Point
1. Flag で Legacy に即時戻す（S6 機構）  
2. それでも不十分な場合: 前リリースの Trigger 決定経路へ戻す（リリース Rollback）

### PASS
- [ ] Production で core DEFAULT 経路が観測ゼロ（またはゲート未満）
- [ ] core は Positive Match のみ
- [ ] unsatisfied が silent core に落ちない
- [ ] V45 再計測で core Compliance がゲート以上、平均 Compliance がゲート以上
- [ ] Rollback 訓練済み

---

## S8 — Downstream Binding（別計画）

### Purpose
Trigger 真理が V44 に安定した後、SubWorld / Role / Candidate Pool /（将来）PE への消費を揃える。

### Depends on
S7 PASS

### Scope（設計・境界）
- **含む:** 下流がどの World ラベルを読むかの契約更新計画
- **含まない（本 Stage 開始時に別 ADR）:** Prediction モデル再学習、PE スコア式の本番変更（V36 I3 は参照のみ）

### Production Decision
項目ごとに別ゲート

### Rollback Point
下流フラグ単位。Trigger Path は S7 状態を維持可能（下流だけ戻す）

### PASS
- 下流各モジュールの個別 ADR に委譲（本 V46 では「S7 後に開く」ことのみ定義）

---

## Stage Exit Rules（共通）

1. PASS チェックリスト未達 ⇒ 次 Stage 禁止  
2. Blocked Must（S2 Missing）⇒ 当該 World の Cutover（S6/S7）禁止  
3. いずれの Stage も **Prediction / PE / CE / AI の同時改修を必須としない**  
4. 実装作業は各 Stage の「実装承認」後にのみ開始（V46 文書自体は承認しない）
