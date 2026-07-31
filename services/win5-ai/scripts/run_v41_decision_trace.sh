#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/KEIBA-Single-AI/services/win5-ai
export PYTHONPATH=/home/ubuntu/KEIBA-Single-AI/services/win5-ai:/opt/expect-ai/platform
python3 -m app.research.world_decision_trace_audit 2>&1 | tee /tmp/v41_run.log
