#!/bin/bash
set -euo pipefail
sed -i 's/\r$//' /tmp/collector_runner.py /tmp/causal_evidence.py
cp /tmp/collector_runner.py /home/ubuntu/KEIBA-Single-AI/services/win5-ai/app/research/collector_runner.py
cp /tmp/causal_evidence.py /home/ubuntu/KEIBA-Single-AI/services/win5-ai/app/research/causal_evidence.py
cd /home/ubuntu/KEIBA-Single-AI/services/win5-ai
python3 -c "from app.research import causal_evidence as m; print('ok', m.SCHEMA_VERSION)"
python3 -m unittest tests.research.test_v21_causal_evidence -v
python3 -m app.research.collector_runner --causal-evidence
