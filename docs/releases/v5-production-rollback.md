# Version 5 — Production Rollback

**Parent:** [`v5-production-deployment-report.md`](./v5-production-deployment-report.md)  
**Affects:** Conversation only（Prediction AI / Ranking / Confidence / Purchase 非対象）

## L1 — All Conversation Flags OFF（推奨・即時）

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

Effect: `conversation.chat` returns Legacy ConversationService. Pages BFF may show stub/legacy-guard for Personal Chat.

## L2 — Knowledge only OFF

Keep Review / Explain / Chat ON; set:

```text
F_V4_KNOWLEDGE_LAYER=OFF
F_V5_KNOWLEDGE_RUNTIME=OFF
```

Then `sudo systemctl restart expect-ai`.

## L3 — UI Pages rollback

Redeploy Pages to pre–V5 Phase 3 UI. Prefer with L1.

## L4 — Code rollback (EC2 git)

```bash
cd /home/ubuntu/KEIBA-Single-AI
# Pre-V5 reflection tip (Version 2 production parity)
sudo -u ubuntu git fetch origin
sudo -u ubuntu git checkout dc99fc4
sudo systemctl restart expect-ai
```

Also apply L1 flags so Orchestrator cannot activate if code still contains V4.

## L5 — Ollama stop (optional)

```bash
sudo systemctl stop ollama
sudo systemctl disable ollama
```

Does not remove Conversation Platform; only disables LLM polish.

## Verify after rollback

```bash
curl -sf http://127.0.0.1:8000/v1/conversation/health | head -c 400; echo
curl -sf -X POST http://127.0.0.1:8000/v1/conversation/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"hello","mode":"chat","context":{"type":"personal_chat","mode":"chat"}}' | head -c 400; echo
```

Expect: no `orchestrator: true` when L1 OFF, or Legacy reply path.
Prediction endpoints unchanged / `mutated` never true from Conversation.
