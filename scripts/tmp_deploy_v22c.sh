#!/bin/bash
set -euo pipefail
BASE=/home/ubuntu/KEIBA-Single-AI/services/win5-ai
sed -i 's/\r$//' /tmp/continuous_research_operation.py /tmp/tmp_inspect_v106.py
cp /tmp/continuous_research_operation.py "$BASE/app/research/continuous_research_operation.py"
python3 /tmp/tmp_inspect_v106.py
cd "$BASE"
python3 -m unittest tests.research.test_v22_continuous_research -v
python3 -m app.research.collector_runner --continuous-research
