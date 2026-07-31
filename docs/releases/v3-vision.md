# Version 3 — Vision

**Date:** 2026-07-22  
**Status:** Design Only（実装・コード変更禁止）  
**Mode:** Version 2 = **保守** / Version 3 = **新世代設計**  
**Control（不変）:** Phase255 + **PE-V2-A ON** · Hit **218**  
**禁止継承:** RP-V2-A / CE-V2-A の再挑戦、V2 Flag 継ぎ足しによる改善継続

---

## 1. なぜ Version 3 か

Version 2 Accuracy は、既存 Pipeline（28 Feature · Phase255 スタック）の上に Flag 付きサイドカーを足す戦略だった。

| V2 結果 | 含意 |
|---------|------|
| PE-V2-A のみ +2 Hit | **場に入れる**レバーはまだ効く |
| RP-V2-A Rescue 0/11 | 「NEAR Rescue」パラダイムは破綻 |
| CE-V2-A Hit −2 / churn | 確率温度の微調整では評価不足を解けない |
| 残 miss（遠位・境界・並べ替え・Delete） | **現行表現空間の天井** |

したがって Version 3 は「V2 の続きの Facet」ではなく、**予測・選定・購入を分離した新アーキテクチャ**として定義する。

```text
Version 2（保守）
  = 本番固定スタック（PE-V2-A）の運用・説明・監視

Version 3（設計）
  = Hit > 218 を狙うための表現・Pool・Selection・Evaluation の再設計
```

---

## 2. Vision Statement

> **Version 3 は、「勝者を場に入れる」だけでは届かない残 miss を、  
> 新しい表現（Feature / 学習）と新しい選定ポリシー（Selection）で解く世代である。  
> RePick は Rescue 装置ではなく、Pool 内並べ替えポリシーに格下げする。  
> Candidate Evaluation は温度ノブではなく、順位付けモデルの責務として再定義する。**

---

## 3. 成功の定義

### 3.1 Primary Goal

| 指標 | Control（V2 Final） | V3 Goal |
|------|--------------------:|--------:|
| Hit（285R） | 218 | **> 218** |
| churn_hit（対 Control） | — | **0** |
| Winner in Pool 率 | 0.961 | 非悪化（目安 ≥ 0.961） |

### 3.2 Secondary（監視・Hard Gate 外だが記録必須）

| 指標 | 方針 |
|------|------|
| Purchase | 大幅増加を禁止（事前に上限案を設計。例: Control の 110% 以内） |
| rank710 / other miss | 減少を目標、悪化は AB FAIL 候補 |
| Delete 後 miss | **変更禁止境界** — 改善手段にしない |

### 3.3 Non-Goals（V3 初期）

- UI / Explain / Ops の大規模再設計（V2 保守のまま）
- Prediction API / RaceCardSummary / PI 契約の破壊
- Delete Boundary の緩和
- 勝者ラベルを Trigger に使うこと
- V2 Flag（RP-V2 / CE-V2）のパラメータ再 AB

---

## 4. 設計原則

| ID | 原則 | 説明 |
|----|------|------|
| P1 | **世代分離** | V2 本番コードは変更しない。V3 は別モジュール / 別 Flag 空間 |
| P2 | **表現が先** | 残遠位 miss は選定ロジックだけでは解けない前提 |
| P3 | **選定はポリシー** | Pool 構築と最終 N 頭選定を明示分離 |
| P4 | **RePick ≠ Rescue** | 旧 RP-NEAR は廃棄。並べ替え専用に再定義 |
| P5 | **単独 AB** | 1 Experiment = 1 Flag。Control は常に V2 Final |
| P6 | **契約ファースト** | 新 Feature は Contract + ROI Validation なしに本番経路へ入れない |
| P7 | **リーク禁止** | 結果・着順・払戻を Trigger / Feature に使わない |

---

## 5. 世代メタファー（責務の言い換え）

```text
V1.1 / Phase255     「1 本のスコアで全部やる」
V2                  「既存スコアに Flag で局所パッチ」
V3（本 Vision）     「表現・場・選定・評価を分離したシステム」
```

| 旧呼び方（V2） | V3 呼び方 | 役割 |
|----------------|-----------|------|
| PE / Pool Entry | **Pool Construction** | 誰を場に入れるか |
| Entry 判定 | **Admission Policy** | 入場条件（匿名・上限付き） |
| RePick | **Selection / Reorder Policy** | Pool 内の並べ替え・枠配分（Rescue しない） |
| Candidate Evaluation | **Ranking / Survival Model** | 順位・生存確率の推定本体 |
| ticket optimizer | **Purchase Mapper** | 選定結果 → 購入計画（Accuracy 本体の外） |

---

## 6. タイムボックス（設計上の意図）

| フェーズ | 内容 | 実装 |
|----------|------|------|
| V3 Design（本ドキュメント群） | Vision / Architecture / Strategy / Roadmap | **禁止** |
| V3-α（将来） | Feature Contract · オフライン実験基盤 | 別承認 |
| V3-β（将来） | 単独 AB · Flag OFF 既定 | 別承認 |
| V3 Production | 採用構成の本番化 | 別承認 |

本 Vision の完了条件は **設計文書の受領**であり、実装開始ではない。

---

## 7. 参照

| 文書 | パス |
|------|------|
| V2 Accuracy Final | `docs/releases/v2-accuracy-final-report.md` |
| V2 Known Limitations | `docs/releases/v2-known-limitations.md` |
| V3 Architecture Proposal | `docs/releases/v3-architecture-proposal.md` |
| V3 Accuracy Strategy | `docs/releases/v3-accuracy-strategy.md` |
| V3 Experiment Roadmap | `docs/releases/v3-experiment-roadmap.md` |
| V3 Design Report（正本） | `docs/releases/v3-design-report.md` |
