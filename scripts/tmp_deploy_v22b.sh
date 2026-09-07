#!/bin/bash
set -euo pipefail
BASE=/home/ubuntu/KEIBA-Single-AI/services/win5-ai
sed -i 's/\r$//' /tmp/continuous_research_operation.py
cp /tmp/continuous_research_operation.py "$BASE/app/research/continuous_research_operation.py"
cd "$BASE"
python3 -m unittest tests.research.test_v22_continuous_research -v
# Re-assemble with first-week noise suppressed; keep existing module outputs
python3 -m app.research.collector_runner --continuous-research-report-only
