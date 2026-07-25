# Version 5 — Production Rollback

**Parent:** [`v5-production-rollout-report.md`](./v5-production-rollout-report.md)  
**Affects:** Conversation only（Prediction AI / Ranking / Confidence / Purchase 非対象）

## L1 — All Conversation Flags OFF（推奨）

```bash
sudo tee /etc/expect-ai/conversation.env >/dev/null <<'EOF'
F_V4_CONVERSATION_ENABLED=OFF
F_V4_REVIEW_AGENT=OFF
F_V4_PERSONAL_CHAT=OFF
F_V4_TOOL_LAYER=OFF
F_V4_KNOWLEDGE_LAYER=OFF
F_V5_KNOWLEDGE_RUNTIME=OFF
F_V4_KNOWLEDGE_INTEGRATION=OFF
F_V4_CONVERSATION_OLLAMA=OFF
EOF
sudo systemctl restart expect-ai
```

## L2 — Knowledge only OFF

Keep Review / Explain / Chat ON; set:

```text
F_V4_KNOWLEDGE_LAYER=OFF
F_V5_KNOWLEDGE_RUNTIME=OFF
```

## L3 — UI Pages rollback

Redeploy Pages to pre–V5 Phase 3 UI. Prefer with L1.

## L4 — expect-ai binary/release rollback

Point `/opt/expect-ai/current` to previous release + keep L1 flags OFF.

## Verify after rollback

```bash
curl -sf http://127.0.0.1:8000/v1/conversation/health
# Prediction endpoints unchanged / mutated never true from Conversation
```
