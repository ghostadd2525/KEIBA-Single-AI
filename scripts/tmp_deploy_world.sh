#!/bin/bash
set -euo pipefail
BASE=/home/ubuntu/KEIBA-Single-AI/services/win5-ai
for f in world_boundary_research.py collector_runner.py; do
  sed -i 's/\r$//' /tmp/$f
  cp /tmp/$f "$BASE/app/research/$f"
done
sed -i 's/\r$//' /tmp/test_v22_world_boundary.py
cp /tmp/test_v22_world_boundary.py "$BASE/tests/research/test_v22_world_boundary.py"
cd "$BASE"
python3 -m unittest tests.research.test_v22_world_boundary -v
python3 -m app.research.collector_runner --world-boundary
