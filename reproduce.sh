#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"

echo "== Verify saved data, criteria, tables, labels, costs, and independent rescoring"
python3 -m approval_relay.cli verify --out results/summary.json

echo "== Regenerate all 12 figures (rendering can vary by platform)"
python3 -m approval_relay.figures --out results/figures

echo "== Offline tests"
python3 -m pytest -q tests

echo "Reproduction complete. No provider credentials or paid calls were used."
