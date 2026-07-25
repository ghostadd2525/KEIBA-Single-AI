# Version 5 — EC2 Reflection Report

**Host:** `ubuntu@13.231.5.5` (`ip-172-31-40-147`)  
**Date:** 2026-07-25  
**Before SHA:** `dc99fc4` (Version 2 era)  
**After SHA:** `b0666f7`

---

## Before

| Item | State |
|------|-------|
| WorkingDirectory | `/home/ubuntu/KEIBA-Single-AI` |
| Conversation package | Legacy only (`service.py` / no `v4` / no `v5`) |
| `scripts/ops/enable-conversation-v5-prod.sh` | Missing |
| `/etc/expect-ai/conversation.env` | Missing |
| `expect-ai.service` EnvironmentFile | `shared/.env` + `pi-core.env` only |
| Ollama | Not installed |
| Personal Chat via BFF | `provider=python_legacy_guarded` |

## After

| Item | State |
|------|-------|
| Git | `main` @ `b0666f7` |
| `app/conversation/v4/orchestrator.py` | Present |
| `app/conversation/v5/knowledge/runtime.py` | Present |
| Deploy script | Present + executable |
| `/etc/expect-ai/conversation.env` | Installed (flags ON · model `qwen2.5:1.5b`) |
| systemd | `EnvironmentFile=-/etc/expect-ai/conversation.env` |
| `expect-ai` | `active` |
| `ollama` | `active` · model `qwen2.5:1.5b` |
| Swap | `/swapfile` 2GiB (LLM headroom) |

## Service unit (excerpt)

```ini
EnvironmentFile=-/opt/expect-ai/shared/.env
EnvironmentFile=-/etc/expect-ai/pi-core.env
EnvironmentFile=-/etc/expect-ai/conversation.env
```

## Flag snapshot (from `/v1/conversation/health`)

```text
F_V4_CONVERSATION_ENABLED=true
F_V4_CONVERSATION_OLLAMA=true
F_V4_REVIEW_AGENT=true
F_V4_PERSONAL_CHAT=true
F_V4_TOOL_LAYER=true
F_V4_KNOWLEDGE_LAYER=true
F_V5_KNOWLEDGE_RUNTIME=true
F_V4_KNOWLEDGE_INTEGRATION=false
```

## Re-deploy

```bash
cd /home/ubuntu/KEIBA-Single-AI
sudo bash scripts/ops/deploy-conversation-v5-prod.sh
# or verify only:
sudo bash scripts/ops/deploy-conversation-v5-prod.sh --verify-only
```
