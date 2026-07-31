# Version30 — Restoration Readiness

**Date:** 2026-07-27  
**Final gate for Design Restoration**

---

## Final判定

# **B — Further Investigation Required**

Design Restoration Ready（A）には **到達していない**。

---

## Ready / Not-ready checklist

| Criterion | Status | Evidence |
|-----------|:------:|----------|
| 設計式の所在が特定できた | Pass | `demo_pace_model_v2.add_win5_leg_difficulty_features` |
| 「削除」ではないと確認 | Pass | 関数・呼び出し元残存 |
| 未呼び出し理由が説明できた | Pass | FG は当初から未呼出 + daily 列欠落 |
| 復元ロケーションが単一に確定 | **Fail** | FG 呼出 vs daily CSV vs pi features — 未決 |
| 設計主契約と FG 復元案が一致 | **Fail** | 主契約は pace→CSV（`v30-contract-gap` G5） |
| Production に式モジュールが存在 | **Fail** | EC2 platform に `.py` 不在 |
| daily 入力がフル式前提を満たす | **Fail** | style_entropy / pace_collapse_risk 欠等 |
| DEFAULT=0.5 の性質が分類できた | Pass | 欠落フォールバック（暫定 Trigger 固定ではない） |
| 影響モジュールが列挙できた | Pass | `v30-risk-assessment` |
| chaos 断絶が同時に閉じる | N/A / Open | difficulty 復元だけでは閉じない |

---

## Why not A

1. **「FeatureGenerator へ戻す」は設計主契約の単純復元ではない**（契約ギャップ G5）。  
2. **現 Production の直接断絶は daily CSV スキーマ縮退**（07-25+）。こちらを調べず FG のみ触ると部分式リスク（R3）。  
3. **モジュール未デプロイ**（D1）。  
4. **入力別名・欠列**（D2–D5）未解決。  
5. pi `build_features` の「legacy exact」主張と実列差分の **意図確認が未了**。

---

## Further investigation items（次フェーズ候補・実装禁止のまま調査）

| ID | Question |
|----|----------|
| F1 | 2026-07-25 daily 72 列化は意図的 Slim か、Shadow/pi 切替副作用か？ |
| F2 | 復元の正規ロケーションは A(FG) / B(daily CSV) / C(pi features) のどれか？ |
| F3 | `pace_collapse_risk_v2` と設計 `pace_collapse_risk` の関係は？ |
| F4 | `field_size` を `horse_count` とみなす契約はあるか？ |
| F5 | 凍結 28 列に difficulty 系が載る現行 schema で、PE 回帰許容条件は？ |
| F6 | chaos_score 断絶は difficulty 復元と分離したまま進めるか？ |

---

## What is already proven（再掲）

- DEFAULT 0.5 は **Production Core**（V29）。  
- 設計式は **削除されていない**。  
- FeatureGenerator は **一度も** add_win5 を呼んでいない（現行・導入コミット）。  
- 旧 daily（≤2026-06-28）では difficulty は **可変**だった。  
- 現行 daily（EC2 07-25/26）では difficulty 列が **無い**。

---

## Deliverables index

| Doc | Path |
|-----|------|
| Design restoration / history | `docs/audit/v30-design-restoration.md` |
| Contract gap | `docs/audit/v30-contract-gap.md` |
| Dependency | `docs/audit/v30-dependency-audit.md` |
| Risk + compatibility inventory | `docs/audit/v30-risk-assessment.md` |
| Readiness (this file) | `docs/audit/v30-restoration-readiness.md` |

---

## Guardrails

- Audit 完了。コード修正・設計復元実装・閾値変更・Production 変更なし。
