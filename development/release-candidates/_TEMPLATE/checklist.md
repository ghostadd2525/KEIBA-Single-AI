# Release Candidate Checklist — {proposal_id}

**前提:** Canary Report `status=pass` であること。FAIL / pending は RC にしない。

## Review

- [ ] Proposal の 5 項目（目的・対象・期待効果・副作用・評価方法）が埋まっている
- [ ] Proposal にコード / パッチが含まれていない
- [ ] Canary Config / Report / Criteria が揃っている
- [ ] Success Criteria をすべて満たしている
- [ ] Rollback Criteria が運用可能である
- [ ] OPS-Monitor / Result Automation を無効化していない
- [ ] Production Prediction Core への無断変更がない

## Decision

- [ ] **Approve** — Deploy runbook へ
- [ ] **Reject** — 理由: ________
- [ ] **Revise** — Proposal に差し戻し

| 項目 | 値 |
|------|-----|
| Reviewer | |
| Reviewed at | |
| Decision | pending_review / approved / rejected |
