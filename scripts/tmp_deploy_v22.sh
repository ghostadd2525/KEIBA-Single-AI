#!/bin/bash
set -euo pipefail
BASE=/home/ubuntu/KEIBA-Single-AI/services/win5-ai
for f in continuous_research_operation.py continuous_research_runner.py collector_runner.py; do
  sed -i 's/\r$//' /tmp/$f
  cp /tmp/$f "$BASE/app/research/$f"
done
sed -i 's/\r$//' /tmp/test_v22_continuous_research.py
cp /tmp/test_v22_continuous_research.py "$BASE/tests/research/test_v22_continuous_research.py"
cd "$BASE"
python3 -m unittest tests.research.test_v22_continuous_research -v
# Full weekly ops (existing modules only)
python3 -m app.research.collector_runner --continuous-research
