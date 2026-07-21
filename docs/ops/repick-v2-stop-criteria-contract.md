# RePick v2 — Stop Criteria Contract

**Contract ID:** `WIN5-REPICK-V2-STOP/1.0`  
**Date:** 2026-07-21  
**Status:** **Active**（Exit Criteria Approved と同時発効）  
**Parent Exit:** [`repick-v2-exit-criteria-contract.md`](./repick-v2-exit-criteria-contract.md)（**Approved**）  
**Parent design:** [`repick-v2-design-review.md`](./repick-v2-design-review.md)  
**Mode:** 終了・除外の事前契約（閾値の事後緩和禁止）

---

## 0. 目的

Exit Criteria は「いつ進むか」を定義する。  
本 Stop Criteria は **「いつ止めるか / Version2 から外すか」** を定義する。

| 用語 | 意味 |
|------|------|
| **Stop** | 追加実装・再 AB・Canary・採用提案を **凍結**。Flag 既定 OFF 維持 |
| **Exclude from V2** | RePick v2 を Version2 ロードマップから **除外（Archive）**。再開は新 Contract（`2.0`）審査のみ |
| **AB attempt** | Control 再現成功後に実行した **正式 AB 1 回**（試行・デバッグ計測は数えない） |

Stop と Exclude は段階がある。Stop のみで「研究保留」もあり得る。Exclude はより重い。

---

## 1. 連続 AB FAIL の終了条件

評価母集団・FAIL 定義は Exit Criteria §1 / §3 に従う。

| ID | 条件 | 結果 |
|----|------|------|
| **ST-F1** | **連続 2 回**の正式 AB が §3 FAIL | **Stop**（追加実装凍結）。原因分析レポート必須 |
| **ST-F2** | **連続 3 回**の正式 AB が §3 FAIL | **Stop + Version2 除外審査開始**（§3 へ） |
| **ST-F3** | 同一 FAIL 系統（例: いずれも AF-1 Hit損失、またはいずれも AF-3 改善率）が **連続 2 回** | **Stop**。設計見直しなしの再実装禁止 |
| **ST-F4** | AB 無効（AF-12 Control 不一致）が **連続 2 回** | **Stop**（環境/ハーネス欠陥）。プロダクト変更禁止 |

### 1.1 「連続」の数え方

```text
正式 AB_PASS → 連続カウンタを 0 にリセット
正式 AB_FAIL → カウンタ +1
デバッグ計測 / Flag 実験ログのみ → カウントしない
契約違反の再計測（AF-11）→ 無効試行（カウントしないが記録必須）
```

### 1.2 Stop 直後の許可・禁止

| 許可 | 禁止 |
|------|------|
| 原因分析（RePick v2 層に限定） | Pool/Entry/Delete/Feature への逃げ実装 |
| Flag OFF 恒等の確認 | 閾値緩和・G1 分母変更 |
| Stop 解除提案（Human + 設計改訂 `1.1`） | 黙って 4 回目 AB |

**Stop 解除:** Human 承認 +（必要なら）Exit/Stop `1.1` 改訂後に、連続カウンタを 0 から再開。

---

## 2. 改善率未達の終了条件

改善率 `R_G1 = G1_rescue / 11`（Exit §1.4）。

| ID | 条件 | 結果 |
|----|------|------|
| **ST-R1** | 正式 AB で `R_G1` **< 4/11** が **通算 2 回**（連続でなくても可） | **Stop** |
| **ST-R2** | 正式 AB で `R_G1` **< 4/11** が **連続 2 回** | **Stop**（ST-F1 と重複し得る。厳しい方を適用） |
| **ST-R3** | AB は PASS（`R_G1≥4/11`）だが、**採用帯 `R_G1≥6/11` に 2 回連続未達** かつ ΔHit **< +2** が同時 | **Stop（採用パス凍結）**。Canary に進まない。研究完了・既定 OFF 維持可 |
| **ST-R4** | Canary C2 まで進んだ後、改善率が G1 再計測で **4/11 未満に後退** | **即 Rollback（Exit §4）+ Stop** |
| **ST-R5** | 匿名トリガを維持したまま、天井分析（Winner-Anchored オフライン上限）が **`R_G1` 上限 < 4/11** と確定 | **Stop + Version2 除外（§3）** — 構造的に AB 合格不能 |

### 2.1 解釈

- **ST-R1/R2:** Exit の AB 合格線（4/11）を繰り返し割れない → 実装継続価値なし。  
- **ST-R3:** 「合格はしたが採用に届かない」状態の打ち切り（無期限 Canary 禁止）。  
- **ST-R5:** 匿名制約下で理論上限不足 → Feature/学習に逃げず **RePick v2 自体を閉じる**。

---

## 3. Version2 から除外する条件

以下の **いずれか**で RePick v2 を Version2 対象から **除外（Archive）**する。

| ID | 条件 | 除外後の扱い |
|----|------|----------------|
| **EX-1** | **ST-F2**（連続 3 回 AB FAIL）成立 | Archive。P0 枠を空け、P1（Pool+Entry）へ移行可 |
| **EX-2** | **ST-R5**（匿名上限 < 4/11）成立 | Archive。Winner-Anchored 再導入による「救済」は禁止 |
| **EX-3** | Exit §7 匿名違反（Winner 直接/間接参照）が **実装後に 1 回でも**確定 | 即 Rollback + **Exclude**（契約違反） |
| **EX-4** | Hit損失（AF-1）が **通算 2 回**の正式 AB で発生 | **Exclude**（Baseline 破壊の反復） |
| **EX-5** | other_miss 悪化（AF-5）または rank710 悪化（AF-4）が **通算 2 回** | **Exclude**（隣接バケツ汚染） |
| **EX-6** | Human が「Version2 除外」を明示承認（本 Stop 以外の経営判断） | Archive |
| **EX-7** | Exit 採用条件（AD-*）を満たせぬまま、**Stop（ST-R3）から 2 評価サイクル**経過し再開提案なし | 自動 **Exclude 候補** → Human 確認後 Archive |

### 3.1 除外時の成果物

1. 本契約および設計・Exit の Status を **ARCHIVED / V2 excluded** に更新  
2. 実装 Flag は **削除または永久 default OFF**（ON パスを製品既定にしない）  
3. 実装チケットを **wontfix または closed-wont-ship**  
4. 後任は P1 Pool+Entry v2（RePick 再開は新 `2.0` Contract のみ）

### 3.2 除外後に禁止すること

- 同一設計のまま閾値だけ下げて再チケット化  
- T-R7N Winner-Anchored を「本番例外」として滑り込ませる  
- PV2-F01 / Learning を RePick 失敗の代替として同時起票（別審査必須）

---

## 4. Stop / Exclude 判定フロー

```text
正式 AB
  ├─ PASS → 連続 FAIL カウンタ=0 → Canary 資格（Exit §5）
  │            └─ 採用帯未達が ST-R3 → Stop（採用パスのみ）
  └─ FAIL → カウンタ+1
             ├─ 連続2 → ST-F1 Stop
             ├─ 連続3 → ST-F2 → EX-1 Exclude 審査
             └─ AF-1/4/5 通算2 → EX-4/5 Exclude
```

---

## 5. 実装チケットとの関係

| イベント | チケット |
|----------|----------|
| Exit Approved + Stop Active | 実装チケット **起票可（1本）** |
| Stop（ST-*）発火 | チケット **blocked**。新規コミット禁止（分析ドキュメントのみ可） |
| Exclude（EX-*）発火 | チケット **wontfix / Archive** |
| Stop 解除（Human + 改訂） | 同一チケット再開可（新チケット乱立禁止） |

---

## 6. 承認欄

| 項目 | 内容 |
|------|------|
| Exit Criteria | **Approved**（2026-07-21） |
| Stop Criteria | **Active**（2026-07-21） |
| 実装チケット | [`issues/ISSUE-REPICK-V2-001-implementation.md`](./issues/ISSUE-REPICK-V2-001-implementation.md) |
