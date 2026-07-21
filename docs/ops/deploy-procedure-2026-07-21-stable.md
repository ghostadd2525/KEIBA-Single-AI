# デプロイ手順 — Stable 2026-07-21

対象: Collector RC-1 + GUI + 一時ID + 運用機能  
**禁止:** `WIN5_REPICK_V2_ENABLED` の ON、予想ロジック Flag 変更

関連: `docs/ops/release-notes-2026-07-21-stable.md` / `docs/ops/release-checklist.md`

---

## 0. 事前

1. 反映する commit SHA を記録する（rollback 用）
2. 本番 SQLite / env のバックアップ
3. Dashboard で Pages secrets が揃っていること（`AI_BASE_URL`, `AI_API_KEY`, Access Token, `OPS_MONITOR_KEY`）
4. **確認:** どのホストの env にも `WIN5_REPICK_V2_ENABLED` が無い / `0` / `false`

---

## 1. Git

```bash
git checkout main
git pull origin main   # または本パッケージ push 後
git log -1 --oneline   # 反映 SHA をメモ
```

---

## 2. Cloudflare Pages（GUI + BFF + 招待 seed）

1. Git 連携プロジェクト `keiba-single-ai` が `main` を追跡していることを確認
2. push 後、Pages の最新 Deployment が **Success** になるまで待つ
3. 手動の場合: Cloudflare Dashboard → Pages → Deployments → Retry / 最新 commit を Deploy
4. スモーク:
   - `https://expect-keiba.com/health`（または Pages URL）→ 200
   - `https://expect-keiba.com/login?id=BETA-F6D1-E07E` → 招待フロー開始
   - `invitation_required` が有効なこと（未招待は拒否）

`public/data/invitations.json` は Pages 静的配信に含まれる。発行後に追加した ID は **再デプロイ**が必要。

---

## 3. EC2 / AI（Python + Collector + 運用）

```bash
cd /path/to/KEIBA-Single-AI
git fetch && git checkout <release-sha>

# venv 有効化後
cd services/win5-ai
python -m app.data.import_csv migrate   # 001…008 適用確認

sudo systemctl restart expect-ai          # 実サービス名に合わせる
sudo systemctl restart cloudflared-expect-ai   # Tunnel 使用時

curl -sS https://ai.expect-keiba.com/health | jq .
# result_automation キーが付くこと（本パッケージ）
```

Collector / Result Automation（有効化済みの場合）:

```bash
sudo systemctl enable --now expect-result-automation.timer
sudo systemctl enable --now expect-ops-monitor.timer
# 例: infra/aws/systemd/
```

**Collector Go-Live HOLD:** Real KeibaNet 本接続前は、本番ジョブを dry-run / Controlled 運用に留める（`docs/ops/collector-rc1-release-review.md`）。

---

## 4. リリース後チェック（短縮）

- [ ] Pages Deployment Success
- [ ] `GET /health` (AI) = ok
- [ ] 一時IDログイン成功（新規 or 既存招待）
- [ ] `GET /api/ops/monitor`（キー付き）が期待どおり
- [ ] `AI_ENGINE=real` 経路で意図しない mock 急増なし
- [ ] **RePick / 予想 Flag が ON になっていない**

詳細は `docs/ops/release-checklist.md`。

---

## 5. Rollback

**Pages:** 前 Deployment を Rollback（Dashboard）  
**AI:** `git checkout <prev-sha>` → migrate 方針確認 → systemd restart  
**DB:** migration 不可逆ならバックアップからリストア

---

## 6. やらないこと

- `WIN5_REPICK_V2_ENABLED=1` の設定
- 研究ツリー Optimizer の本番同期（本リリース範囲外）
- Collector の Real KeibaNet 本接続宣言（HOLD 解除前）
