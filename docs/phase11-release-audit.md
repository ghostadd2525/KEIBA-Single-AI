# Phase11: Release Audit（β公開判定）

**Status:** Audit only（コード / IaC / API / UI / 設計変更なし）  
**Date:** 2026-07-20  
**視点:** 第三者リリースレビュー  
**対象:** Frontend / Prediction / Analysis / Kaoba / Auth / Invitation / Cloudflare Access / BFF / Python AI / CLI / Audit Log / beta.json / ドキュメント

---

## β公開判定

# **CONDITIONAL GO**

| 判定 | 条件 |
|------|------|
| **CONDITIONAL GO** | Cloudflare Access が許可リスト付きで適用済みであり、下記 MUST FIX（M1–M4）を**運用で閉じた**うえで、限定テスターのみに開放する |
| **NO GO（実質）** | Access 未適用、または Everyone 開放、または M1–M4 未実施のまま Pages を一般到達可能にする場合 |
| **GO** | 非該当（現状のまま無条件公開は不可） |

契約・テスト・運営 CLI・Python 公開バインド拒否・ドキュメントは揃っている。ブロッカーは**外周 Access の実適用確認**と**招待制を成立させる運用ゲート**である。

---

## 1. PASS項目

| ID | 項目 | 根拠 |
|----|------|------|
| P1 | PredictionBundle / Analysis / Kaoba / Auth の契約整合 | `npm test` **60/60 PASS**。fixtures ↔ `contracts/**` |
| P2 | BFF レスポンス envelope | `tests/bff/snapshots.test.mjs` |
| P3 | Python AI の公開バインド拒否 | `services/win5-ai/app/main.py` — 既定 `127.0.0.1`、`0.0.0.0` は `AI_ALLOW_PUBLIC_BIND` 必須 |
| P4 | 実シークレットのリポジトリ混入なし | `.dev.vars` は gitignore。example はプレースホルダのみ |
| P5 | β運営 CLI（issue/list/disable/enable/show/reset-password） | `scripts/beta-admin.mjs` + `tests/contract/beta-ops.test.mjs` |
| P6 | 監査ログ JSONL 構造 | `functions/_lib/auditLog.js`、CLI 追記、middleware の利用監査 |
| P7 | `beta.json` 運営設定 | `config/beta.json` と `public/config/beta.json` 同期 |
| P8 | 運営マニュアル・公開前チェックリスト | `docs/beta-operation.md`, `docs/beta-security-checklist.md` |
| P9 | Kaoba BFF の rule フォールバック | Python 失敗時も契約維持（旧 502 問題は修正済み） |
| P10 | 招待状態機械 | issued / activated / disabled / expired — `invitation-state` テスト |
| P11 | Phase9-A IaC 一式の存在 | `infra/cloudflare`（apply は管理者責務） |
| P12 | Auth ログイン／setup／invite の応答形 | `expect-auth/1.0` と一致 |

---

## 2. WARNING項目

| ID | 項目 | 影響 | 推奨（将来・本監査では未実施） |
|----|------|------|--------------------------------|
| W1 | Prediction / Analysis / Kaoba が Bearer **任意** | Access 内側の共有端末でも API 直叩き可 | Bearer 必須化（契約は 401 のみ） |
| W2 | stub トークンに **署名なし** | 到達者は任意 `sub` を偽造可能 | HMAC / Access JWT 検証 |
| W3 | FE 認証は localStorage + リダイレクトのみ | UX ガードでありセキュリティ境界ではない | サーバ強制（W1）とセット |
| W4 | `aiFetch` に timeout / retry なし | 不通時ハングまたは即 502 | AbortController + 限定リトライ |
| W5 | Prediction/Analysis は AI 不通で 502（Kaoba と非対称） | 運用監視が必要 | 方針の明示的合意 |
| W6 | `invitation_required` がコード未参照 | フラグ見た目のみ | 配線または docs から「将来用」明記強化 |
| W7 | 監査は成功中心（失敗 API・favorites 未網羅） | インシデント調査が弱い | 失敗イベント追加 |
| W8 | パスワード方針が弱い（長さ≥8、固定ソルト SHA-256） | ハッシュ漏洩時のオフライン推測 | Argon2 等（設計変更） |
| W9 | login / invite にレート制限なし | ブルートフォース耐性低 | Access + 将来 WAF/レート |
| W10 | `AI_API_KEY` 未設定時は鍵チェックスキップ | Tunnel 漏洩時の第二鍵なし | staging/prod で必須化 |
| W11 | FE 重複・未使用経路（`client.js` 等）、tickets/confidence 分岐 | 保守コスト | 整理（別フェーズ） |
| W12 | `/api/auth/me` は disabled ユーザーでも有効トークンなら 200 | 停止後もセッション残存 | me で status 再検証 |
| W13 | メンテ設定読込失敗時 fail-open | メンテ遮断が効かない | fail-closed 検討 |
| W14 | `public/config/beta.json` 公開 | 運営フラグの偵察材料 | 許容範囲（機密ではない） |

---

## 3. MUST FIX項目（公開ゲート）

本監査はコード変更禁止のため、**運用で閉じる**前提。閉じられない場合は公開延期（NO GO）。

| ID | 項目 | 理由 | 閉じ方（コード変更なし） |
|----|------|------|--------------------------|
| **M1** | Cloudflare Access の apply + 許可リスト確認 | 未適用または `everyone` だと招待制が成立しない。TF は許可メール空で Everyone フォールバック | 管理者が apply。メール限定。未認証アクセス拒否を手動確認。チェックリスト A 全項目 |
| **M2** | 本番 seed からデモ招待・`demo-user` 除去 | `/data/invitations.json`・`users.json` が静的公開。docs に `demo-pass` 記載 | 本番デプロイ前に `disable` / 削除し再デプロイ。デモは staging のみ |
| **M3** | 招待 activate / ユーザー作成の永続化運用 | Workers Isolate メモリのみ。コールド後、seed 上は `issued` のまま同一一時IDを再利用し得る | activate 後は CLI で JSON 更新し即デプロイ、または同時利用者1名＋監視。恒久は将来 KV/D1 |
| **M4** | FE 無音 mock の運用合意 | `prediction.js` / `analysis.js` が API 失敗時に mock 成功扱い → 障害を隠蔽 | β期間は AI/Tunnel 常時健全を監視。異常時は `maintenance_mode: true`。将来は障害明示 UI |

---

## 4. リスク一覧

| リスク | 深刻度 | シナリオ | 緩和 |
|--------|--------|----------|------|
| Access 外周欠落 | **Critical** | Pages 到達者が invitations・予測 API・stub 偽造にアクセス | M1 |
| 招待再利用 | **High** | 別 Isolate / 再起動後に同一一時IDで再登録 | M3 |
| デモ資格情報露出 | **High** | 静的 `users.json` + 固定ソルト + docs 平文パス | M2 |
| 障害隠蔽 | **Medium** | AI 死んでも FE がモックを「本物」として表示 | M4 |
| stub 偽造 | **High**（Access なし）/ **Medium**（Access あり） | 任意 user の me/favorites | Access 厳格 + 将来署名 |
| AI 直公開 | **High**（誤設定時） | `0.0.0.0` + 鍵なし | コードは拒否済み。運用で `AI_ALLOW_PUBLIC_BIND=0`・Tunnel 維持 |
| Everyone ポリシー誤 apply | **Critical** | tfvars 空のまま apply | M1・tfvars レビュー |

---

## 5. 領域別所見（要約）

### セキュリティ
- 設計は **Access が外周、アプリは stub 認証**。Access なしでは招待制βとして不合格。
- Python 公開バインド拒否は **PASS**。
- Secrets の実値コミットは見当たらず **PASS**（デモ seed は別問題 → M2）。

### API契約
- PredictionBundle / Analysis / Kaoba / Auth は設計どおり維持 **PASS**。
- 意図的仕様: 閲覧 API の Bearer 任意（`phase9-access-control.md` 記載）→ **WARNING (W1)**。

### リリース品質
- 例外は概ね `jsonError` envelope。
- timeout/retry 不足、FE 無音 mock が品質上の主リスク（W4, M4）。
- Kaoba の BFF フォールバックは良好。

### 運営性
- CLI・マニュアル・チェックリスト・beta.json・監査基盤は **PASS**。
- ただし招待の Workers 非永続はマニュアル記載ありつつ、β公開の実務ブロッカー（M3）。

### 保守性
- TODO は Python Analysis/Kaoba 本実装寄り。致命的 dead code による公開阻害はなし。
- FE 重複経路は WARNING。

---

## 監査方法

- リポジトリ静的レビュー（auth / middleware / adapters / FE api / infra / seed / docs）
- 既存テスト結果の確認（60/60）
- Phase9-A/B・Phase10・セキュリティチェックリストとの突合
- **実施していないこと:** 本番 Cloudflare アカウントへのログイン確認、実 Traffic 侵入テスト、コード変更

---

## 参照

- [`docs/phase10-beta-release-preparation.md`](./phase10-beta-release-preparation.md)
- [`docs/beta-operation.md`](./beta-operation.md)
- [`docs/beta-security-checklist.md`](./beta-security-checklist.md)
- [`docs/phase9-a-access-infrastructure.md`](./phase9-a-access-infrastructure.md)
- [`docs/phase9-b-invitation-auth.md`](./phase9-b-invitation-auth.md)

---

## 結論（一文）

**招待制βは「Access 適用済み＋デモ seed 清掃＋招待永続化運用＋AI健全監視」を条件付きで公開可能（CONDITIONAL GO）。条件未充足なら NO GO。**
