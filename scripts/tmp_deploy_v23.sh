#!/bin/bash
set -euo pipefail
BASE=/home/ubuntu/KEIBA-Single-AI/services/win5-ai
for f in corpus_growth.py collector_runner.py; do
  sed -i 's/\r$//' /tmp/$f
  cp /tmp/$f "$BASE/app/research/$f"
done
sed -i 's/\r$//' /tmp/test_v23_corpus_growth.py
cp /tmp/test_v23_corpus_growth.py "$BASE/tests/research/test_v23_corpus_growth.py"
cd "$BASE"
python3 -m unittest tests.research.test_v23_corpus_growth -v
python3 -m app.research.collector_runner --corpus-growth
