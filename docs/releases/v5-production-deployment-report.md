# Version 5 — Production Deployment Report

**Date:** 2026-07-25 (JST)  
**Status:** Production Reflection COMPLETE  
**Host:** EC2 `13.231.5.5` (`ip-172-31-40-147`) · service `expect-ai`  
**Release SHA:** `b0666f7` (`main`)  
**Scope:** Conversation Platform (V4) + Knowledge Runtime (V5) reflection only  
**Out of scope:** Prediction AI ranking/confidence/purchase · Memory

---

## 1. Why EC2 lacked V5

| Observation | Cause |
|-------------|--------|
| `conversation/v4` / `v5` missing | Packages existed only in a **local untracked working tree** — never committed to `origin/main` |
| `enable-conversation-v5-prod.sh` missing | Same — ops scripts were local-only |
| `git log` stopped at Version 2 (`dc99fc4`) | EC2 had not pulled later commits; V5 code was not on remote until this deployment |

**Root cause:** Production Reflection gap (code not on `main`), not a systemd-only flag miss.

---

## 2. Inventory (required files)

### Runtime code
- `services/win5-ai/app/conversation/__init__.py` (V4 gate)
- `services/win5-ai/app/conversation/v4/**` (Orchestrator · Agents · Tools · Security · Prediction Read Only · History)
- `services/win5-ai/app/conversation/v5/knowledge/**` (Knowledge Runtime)
- `services/win5-ai/app/main.py` (`/v1/conversation/health` · `/v1/conversation/chat`)

### Config / systemd
- `services/win5-ai/config/production/conversation.env`
- `infra/aws/systemd/conversation.env.example`
- `infra/aws/systemd/expect-ai.service.example`
- Installed: `/etc/expect-ai/conversation.env`
- Wired: `EnvironmentFile=-/etc/expect-ai/conversation.env` on `expect-ai.service`

### Deploy scripts
- `scripts/ops/deploy-conversation-v5-prod.sh` (**canonical Production Deploy Script**)
- `scripts/ops/enable-conversation-v5-prod.sh` (wrapper → deploy script)

### Docs / ADRs / tests
- `docs/adr/ADR-001` … `ADR-005`
- `docs/releases/v5-*`
- `services/win5-ai/tests/ops/test_conversation_v4_*.py`
- `services/win5-ai/tests/ops/test_conversation_v5_knowledge_runtime.py`
- `services/win5-ai/tests/ops/verify_conversation_v5_production.py`

---

## 3. Deployment steps executed

1. Commit + push Conversation V5 to `origin/main` (`126416e` … `b0666f7`)
2. EC2: `git reset --hard origin/main` → SHA `b0666f7`
3. `sudo bash scripts/ops/deploy-conversation-v5-prod.sh --skip-git --model qwen2.5:1.5b`
4. Install Ollama + 2GiB swap (t3.small memory headroom)
5. Pull model `qwen2.5:1.5b`
6. Restart `expect-ai` with Conversation flags ON

**Model note:** Instance has ~2GiB RAM. Production env uses `qwen2.5:1.5b` (not `qwen3:8b`) so `llm.ollama_called=true` is achievable. Upsize host before upgrading model.

---

## 4. Stop condition (met)

| Check | Result |
|-------|--------|
| EC2 `/v1/conversation/chat` Personal Chat | `agent=chat` · `orchestrator=true` · `llm.ollama_called=true` |
| Public `https://expect-keiba.com/api/conversation/chat` | **Not** `python_legacy_guarded` · `agent=chat` · `orchestrator=true` · `ollama_called=true` |
| Conversation health flags | All V4/V5 Canonical flags ON (Integration OFF) |

---

## 5. Related artifacts

- [EC2 Reflection Report](./v5-ec2-reflection-report.md)
- [Verification Result](./v5-production-verification-result.md)
- [Rollback Procedure](./v5-production-rollback.md)
- Deploy script: `scripts/ops/deploy-conversation-v5-prod.sh`
