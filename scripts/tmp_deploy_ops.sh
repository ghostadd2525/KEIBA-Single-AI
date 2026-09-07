#!/bin/bash
set -euo pipefail
BASE=/home/ubuntu/KEIBA-Single-AI/services/win5-ai
sed -i 's/\r$//' /tmp/continuous_research_operation.py /tmp/collector_runner.py
cp /tmp/continuous_research_operation.py "$BASE/app/research/continuous_research_operation.py"
cp /tmp/collector_runner.py "$BASE/app/research/collector_runner.py"
cd "$BASE"
python3 -c "from app.research.continuous_research_operation import DEFAULT_PIPELINE; print([s[0] for s in DEFAULT_PIPELINE])"
python3 -m app.research.collector_runner --research-ops
