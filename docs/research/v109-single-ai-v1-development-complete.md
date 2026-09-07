# Single AI Version1 — Development Completion & Freeze Declaration

**宣言日:** 2026-07-29  
**効力:** 即時  
**ステータス:** **DEVELOPMENT COMPLETE** · **OPERATIONS MANAGEMENT PHASE**  
**Feature Flag:** `single_ai_detail` = **OFF（維持必須）**

---

## 1. 宣言文

**Single AI Version1 の開発フェーズを完了する。**

以下を **完了** とする。

| 領域 | 状態 |
|---|---|
| Core Platform Version1 | **完了 · FROZEN** |
| Single AI Version1 | **完了 · FROZEN（新規機能停止）** |
| Consumer | **完了 · FROZEN（V1 範囲）** |
| HTTP Integration（A1 / Site / BFF） | **完了** |
| Existing UI Integration（I1–I3 / UI1–UI2） | **完了** |
| Race List Cache | **完了 · LOCK（永久）** |
| Operational Readiness（I4–I5） | **完了** |
| Production Release（R1 · Flag OFF） | **完了** |

以後、Single AI Version1 に対する **新規機能追加を停止**する。  
製品は **運用管理フェーズ**へ移行する。

---

## 2. 運用管理フェーズで許可されること

| 許可 | 例 |
|---|---|
| 監視・警報・Runbook 運用 | ALT-SD* · `/api/ops/single-detail` · monitor |
| 致命的欠陥の最小 Hotfix | 別コミット · 挙動を変えない範囲 |
| 文書・監査・証跡の追記 | ops / research 史実の追加（改ざん禁止） |
| Platform 正常化作業 | Single V1 機能追加を伴わない障害対応 |
| **別 Gate** としての恒久 Cutover 準備 | 下記 §4 の条件をすべて満たした後のみ |

## 3. 禁止（Single AI Version1）

| 禁止 | 例 |
|---|---|
| 新規機能追加 | 新 API ・新 UI 枠 ・新 Flag 既定 ON |
| Core / Consumer / Prediction / Contract 変更 | V1 名目の Improvement |
| UI レイアウト変更 | prediction-bind 見た目の改変 |
| Race List Cache 変更 | キー・TTL・更新方法・一覧 Single 接続 |
| 独断の恒久 Flag ON | 承認なき `single_ai_detail: true` 本番常時 |

**Rollback / 安全既定:** `single_ai_detail: false` を維持する。

---

## 4. 恒久 Cutover — 別 Gate

恒久 Cutover（一般トラフィック向け Flag ON）は **本完了宣言の範囲外**であり、次をすべて満たした後の **別 Gate** とする。

1. **Platform 正常化**（health / critical probe が許容範囲）
2. **運用承認**（on-call / ops sign-off）
3. **Release Decision**（明示の Cutover GO 文書）

参照:

- `docs/research/v109-r1-final-recommendation.md`
- `docs/research/v109-i2-final-cutover-gate-after-r1.md`
- `docs/ops/single-detail-operation-guide.md`

Cutover Gate 名（推奨）: **Single AI V1 Cutover Gate（post-ops）**

---

## 5. フェーズ遷移

```text
[ Development Phase — CLOSED ]
        │
        ▼
[ Operations Management Phase — ACTIVE ]
        │
        │  (Platform 正常化 + 運用承認 + Release Decision)
        ▼
[ Cutover Gate — NOT OPEN ]
```

---

## 6. 関連正本

| 文書 | 役割 |
|---|---|
| `docs/adr/PLATFORM-V1-CONTRACT.md` | Core Platform V1 Freeze |
| `docs/research/v109-migration-plan.md` | V109 系列（本宣言で開発完了追記） |
| `docs/ops/single-detail-*.md` | 運用正本 |
| `docs/research/v109-r1-*.md` | Production Release 証跡 |
| `docs/research/v109-single-ai-v1-ops-phase.md` | 運用管理フェーズ憲章 |

---

## 7. Decision 記録

```
【Decision】
Action Type: Development Completion / Phase Transition
Implementation Required: No（新規機能なし）
Deployment Required: No（追加デプロイ不要 · Flag OFF 維持）
Configuration Required: Yes — single_ai_detail=false 維持
Production Required: Ops management only
Rollback Required: N/A
Risk: Low
Expected Next Action: 運用監視 · Cutover は別 Gate
```
