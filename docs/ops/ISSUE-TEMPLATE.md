# Issue テンプレート（Beta Operation Mode）

Issue ごとにこの構成で進め、同じ構成で成果物を残す。  
パス例: `docs/ops/issues/ISSUE-001-<slug>.md`

```markdown
# ISSUE-XXX: <タイトル>

- Priority: P0 | P1 | P2 | P3 | P4
- Status: open | in_progress | done | wontfix
- Baseline: v1.0.0-beta

## 1. 原因
（根本原因。推測と確定を分ける）

## 2. 影響範囲
（ユーザー / API / 画面 / 運営 / セキュリティ）

## 3. 修正内容
（何をどう変えるか。契約・UI・IaC に触れる場合は明示し承認を得る）

## 4. リスク
（回帰・データ・公開面）

## 5. テスト
（手順と結果）

---

## 設計
（方針・触るファイル・やらないこと）

## 実装
（差分要約。必要なら PR リンク）

## テスト結果
（PASS/FAIL・コマンド）

## リリースノート
（テスター / 運営向け短文）
```

## 凍結（変更時は明示承認）

- PredictionBundle 契約
- Analysis API 契約
- Kaoba API 契約
- Cloudflare IaC（管理者承認必須）
