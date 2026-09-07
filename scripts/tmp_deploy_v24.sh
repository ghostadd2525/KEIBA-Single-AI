#!/bin/bash
set -euo pipefail
BASE=/home/ubuntu/KEIBA-Single-AI/services/win5-ai
for f in world_activation_research.py collector_runner.py; do
  sed -i 's/\r$//' /tmp/$f
  cp /tmp/$f "$BASE/app/research/$f"
done
sed -i 's/\r$//' /tmp/test_v24_world_activation.py
cp /tmp/test_v24_world_activation.py "$BASE/tests/research/test_v24_world_activation.py"
cd "$BASE"
python3 -m unittest tests.research.test_v24_world_activation -v
python3 -m app.research.collector_runner --world-activation
