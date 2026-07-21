# Release Readiness（Phase12）

**Date:** 2026-07-20  
**前提:** Phase11 = CONDITIONAL GO（M1–M4 MUST FIX）  
**本 Phase:** リリースゲート閉鎖（契約・UI・IaC 構造・新機能は変更せず）

---

## ゲート完了状況

| Gate | 内容 | 状態 | 成果物 |
|------|------|------|--------|
| **M1** | Cloudflare Access 適用確認手順の最終化 | **完了** | [`release-access-check.md`](./release-access-check.md) |
| **M2** | デモ資格情報除去 | **完了** | [`release-seed-review.md`](./release-seed-review.md) + seed/docs 更新 |
| **M3** | Invitation 永続化運用の明文化 | **完了** | [`invitation-operation.md`](./invitation-operation.md) |
| **M4** | Mock / AI 障害時運用 | **完了** | [`ai-incident-runbook.md`](./ai-incident-runbook.md) |

### M1 補足

リポジトリ上のゲートは「確認手順・サインオフ欄の整備」まで完了。  
**実アカウントでのダッシュボード確認・サインオフ**は公開直前に管理者が [`release-access-check.md`](./release-access-check.md) で実施する（IaC 勝手変更なし）。

### M2 補足

- `public/data/users.json` / `invitations.json` → 空配列  
- docs / integration-check から平文 `demo-pass` 除去  
- 契約フィクスチャは `fixture-user`（平文パスワード非記載）

### M3 補足

実装（KV/D1）は行わず、発行・activate 後 disable・バックアップ・復旧を運用で固定。

### M4 補足

FE 無音 mock はコード変更せず、メンテ切替・監視・テスター事前告知で閉じる。

---

## 残リスク

| リスク | 深刻度 | 扱い |
|--------|--------|------|
| M1 サインオフ未実施のまま URL 配布 | Critical | **禁止。** 未サインオフなら運用上公開不可 |
| stub トークン署名なし / API Bearer 任意 | Medium | Access 外周前提で受容（Phase11 WARNING） |
| 招待の Workers 非永続 | Medium | M3 運用で緩和。将来 KV/D1 |
| FE 無音 mock | Medium | M4 メンテ優先・事前告知で緩和 |
| パスワード方針（固定ソルト SHA-256） | Low–Med | β限定で受容 |
| 監査の失敗イベント不足 | Low | 受容 |

---

## 最終公開判定

# **GO**

**条件付き実務ルール（必須）:**

1. テスターへの URL / 一時ID 配布前に [`release-access-check.md`](./release-access-check.md) を全項目 PASS でサインオフする  
2. [`invitation-operation.md`](./invitation-operation.md) に従い、setup 後は招待を失効させてデプロイする  
3. 障害時は [`ai-incident-runbook.md`](./ai-incident-runbook.md) に従い、迷ったら `maintenance_mode: true`  
4. 本番 seed にデモユーザーを戻さない  

上記を守る限り、招待制βとして **GO**。  
M1 未サインオフでの一般到達可能な公開は **不可**（その場合のみ運用判断を NO GO とする）。

---

## 変更ファイル一覧（Phase12）

| パス | 内容 |
|------|------|
| `docs/release-access-check.md` | M1 |
| `docs/release-seed-review.md` | M2 記録 |
| `docs/invitation-operation.md` | M3 |
| `docs/ai-incident-runbook.md` | M4 |
| `docs/release-readiness.md` | 本ファイル |
| `public/data/users.json` | 空 seed |
| `public/data/invitations.json` | 空 seed |
| `fixtures/auth/*` | デモ資格情報排除 |
| `docs/phase9-*.md` / `auth-service.md` / `beta-operation.md` | 平文削除 |
| `docs/integration-check/body-*.json` | 平文削除 |
| `tests/bff/__snapshots__/auth-*.envelope.json` | fixture-user 追従 |

---

## 参照

- [`phase11-release-audit.md`](./phase11-release-audit.md)  
- [`beta-security-checklist.md`](./beta-security-checklist.md)  
- [`beta-operation.md`](./beta-operation.md)  

## Phase13（公開当日支援）

- [`launch-day-runbook.md`](./launch-day-runbook.md) — 適用順序・当日タイムライン  
- [`rollback-runbook.md`](./rollback-runbook.md) — 失敗時復旧  
- [`health-checklist.md`](./health-checklist.md) — 公開直後確認  
- [`beta-monitoring.md`](./beta-monitoring.md) — β期間の毎日監視  

## 以降

**Beta Operation Mode** — ベースライン [`baseline-v1.0.0-beta.md`](./baseline-v1.0.0-beta.md)。新フェーズなし。Issue のみ。

### AWS（ISSUE-AWS-001）

- [`aws-architecture.md`](./aws-architecture.md)
- [`aws-deployment.md`](./aws-deployment.md)
- [`aws-security.md`](./aws-security.md)
- [`aws-operations.md`](./aws-operations.md)
- [`aws-cost-estimate.md`](./aws-cost-estimate.md)
- IaC 骨格: `infra/aws/`
