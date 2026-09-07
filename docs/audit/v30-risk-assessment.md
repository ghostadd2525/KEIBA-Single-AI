# Version30 — Risk Assessment

**Date:** 2026-07-27  
**前提:** 設計式復元を **仮説**として評価。改善実装・閾値変更は禁止。

---

## ④ Compatibility blast radius（影響モジュール一覧）

| Module | Impact if designed difficulty restored | Nature |
|--------|----------------------------------------|--------|
| PE | 凍結 28 列に difficulty / leg_* が含まれる場合、入力値が定数 0.5 から可変へ | Direct |
| CE | meta.`race_leg_difficulty` 変化 → World 分類入力変化 | Direct |
| World Trigger | R2/R7 等の difficulty 閾値が実効化・分布変化 | Direct |
| SubWorld | World ラベル変化に追随 | Indirect |
| Role | World/SubWorld 依存なら変化 | Indirect |
| Candidate Pool | 下流プール・生存割当 | Indirect |
| Research | Snapshot difficulty 分布・V26–V28 指標 | Direct (observe) |
| AI / Prediction Bundle | Bundle 数値非搭載でも World 永続経路は影響しうる | Indirect |
| Challenge / ResultAutomation | 購入・結果分布が変わりうる | Indirect |
| chaos_score | **非解消**（別断絶） | None (difficulty-only) |

Restore locus 別:

| Locus | Extra surface |
|-------|---------------|
| FG 内呼出 | Core feature 境界・deploy に `demo_pace_model_v2` 要否 |
| daily CSV legacy 復帰 | FeatureLoader 入力スキーマ全体（46 列級） |
| pi `build_features` 追加 | pi-keibanet feature 契約 |

---

## 想定リスク

| ID | Risk | Severity | Notes |
|----|------|----------|-------|
| R1 | World 割当分布の急変（midupper 飽和 → 他 World 出現） | High | Trigger コード不変でも入力可変で挙動変化 |
| R2 | PE Ranker 入力変化による score/prob 回帰 | High | difficulty 系が 28 列に含まれる |
| R3 | 部分入力での「偽設計値」（style_entropy / pace_collapse=0） | High | 設計フル式と不一致のまま Trigger が動く |
| R4 | `pace_collapse_risk_v2` 誤接続・未接続 | Medium | 別名ギャップ |
| R5 | FG に式を入れること自体が「境界アダプタ」契約違反 | Medium | 設計主契約は CSV 搬送 |
| R6 | EC2 にモジュール不在で ImportError | High（未同梱時） | platform に `.py` なし |
| R7 | chaos 未修復のまま difficulty だけ動く非対称 | Medium | bug/mixed はなお不通の可能性 |
| R8 | Research と Production の一時的不一致（段階ロールアウト時） | Medium | |

---

## 想定メリット（事実ベース・提案ではない）

| ID | Benefit if true designed values return |
|----|----------------------------------------|
| B1 | Trigger の difficulty 閾値が定数通過ではなく信号として機能しうる |
| B2 | V28「unique_n=1 / std=0」状態の解消が見込める（旧 daily では unique_n≥5） |
| B3 | Research Snapshot が設計式由来の difficulty を観測可能 |
| B4 | 設計マップ（pace → market → Core）との整合が回復しうる（locus が CSV 側の場合） |

---

## 回帰リスク

| Surface | Regression mode |
|---------|-----------------|
| World mix | 設計目標 mix へ近づく可能性と、予期せぬ World 偏り両方 |
| Purchase / Pool | Role・Pool 連鎖でチケット構成が変化 |
| Ranker | win_prob / model_rank の日次分布シフト |
| Ops CSV | 116 列復帰は compare ガード・Shadow 切替と衝突しうる（07-25 unblock 経緯） |
| Idempotency | FG 二重適用や enrich 前後順で値上書きリスク |

---

## Risk × readiness implication

- **高リスクかつ未解決（D1–D6 / G5）があるため、即座の安全復元は不可。**  
- メリット（B1–B4）は存在するが、**復元ロケーション未決**のまま実装すると R3/R5 が顕在化しやすい。

---

## Guardrails

- リスク評価のみ。緩和策の実装・閾値緩和・改善コードなし。
