# β公開前セキュリティチェックリスト（Phase10）

公開前にすべて確認し、未達は公開延期。

---

## A. Cloudflare Access

- [ ] 本番/ステージングの Access Application が意図したホストのみを保護している
- [ ] 許可ポリシー（メール / IdP グループ）がβテスターに限定されている
- [ ] 一般公開（Everyone / 無制限）になっていない
- [ ] Tunnel 経由の Python AI ホストが Access で保護されている
- [ ] BFF→AI の Service Token（Client ID/Secret）が Pages secrets にあり、リポジトリに無い
- [ ] DNS / Terraform apply は承認済み担当のみ（Phase10 では IaC 勝手変更なし）
- [ ] ブラウザで未認証アクセスが拒否されることを手動確認した

---

## B. Invitation

- [ ] `invitation_required: true`（`config/beta.json` / `public/config/beta.json`）
- [ ] デモ用以外の不要な `issued` 招待を整理、または `disable` 済み
- [ ] `BETA-DISABLED-*` / 期限切れサンプルが本番 seed に残っていない（または無効のまま）
- [ ] 発行は CLI（`npm run beta -- issue`）のみ。推測困難な ID
- [ ] 一時IDをチャット等に平文で広く晒していない
- [ ] activated 済み招待の再利用が拒否されることを確認した

---

## C. Auth

- [ ] 正式ログインはログインID + パスワードのみ（一時ID直ログイン不可）
- [ ] 停止ユーザー（`status: disabled`）が 403 になる
- [ ] パスワードハッシュが平文で保存されていない（`sha256$...`）
- [ ] setup / login のレスポンスにパスワードが含まれない
- [ ] `/api/auth/me` / favorites が不正トークンで 401
- [ ] 利用規約同意なしで setup できない
- [ ] 監査: ログイン成功/失敗・招待利用・初回設定が記録される（Workers console または JSONL）

---

## D. Prediction API

- [ ] レスポンス契約（PredictionBundle / envelope）を変更していない
- [ ] Python AI が `0.0.0.0` 公開バインドしていない
- [ ] `AI_BASE_URL` が Tunnel/内部向けであり、インターネット直ではない
- [ ] メンテ時（`maintenance_mode: true`）に予測 API が 503 になる
- [ ] 成功利用時に監査 `prediction_used` が出る（audit.enabled）
- [ ] `npm test` の Prediction 契約テストが PASS

---

## E. Kaoba API

- [ ] Kaoba 契約（request/response schema）を変更していない
- [ ] `/api/kaoba/chat` が Access 内側でのみ到達可能
- [ ] 失敗時に UI/契約を壊すエラーを返していない（既存フォールバック維持）
- [ ] 成功利用時に監査 `kaoba_used` が出る
- [ ] `npm test` の Kaoba 契約テストが PASS

---

## F. Analysis API（参考・同梱確認）

- [ ] Analysis 契約を変更していない
- [ ] 成功利用時に監査 `analysis_used` が出る
- [ ] 契約テスト PASS

---

## G. 運営準備

- [ ] [`beta-operation.md`](./beta-operation.md) を運営者が読んだ
- [ ] CLI（issue/list/disable/enable/show/reset-password）の動作確認済み
- [ ] `maintenance_mode` の ON/OFF 手順を把握している
- [ ] 障害時の連絡先・ロールバック（前バージョン Pages デプロイ）を決めている
- [ ] 監査ログの収集先（wrangler/Logpush またはローカル JSONL）を決めている
