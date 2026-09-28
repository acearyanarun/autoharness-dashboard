#!/usr/bin/env bash
# Rebuild the dashboard's bundled dataset (the 2026-09-17 controlled baseline) and verify it.
# Output: web/public/data/  (served by `npm run dev` and copied into the production build).
#
# Usage: scripts/build-baseline-data.sh [OUT_DIR]
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-web/public/data}"
BASELINE=fixtures/baseline-2026-09-17-x86_64

rm -rf "$OUT"
python -m autoharness_data build \
  --adapter per-function-json-v1 \
  --listing "$BASELINE/golden/practicum-autoharness-functions.json.gz" \
  --run-meta "$BASELINE/run-meta.toml" \
  --expect "$BASELINE/expected.toml" \
  --out "$OUT"
python -m autoharness_data verify --data "$OUT"
