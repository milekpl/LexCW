#!/usr/bin/env bash
set -euo pipefail

export E2E_DEBUG_STATE=1
export LOG_LEVEL=DEBUG
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

mkdir -p tests/e2e/logs/individual_node_runs
mkdir -p tests/e2e/logs/full_run_artifacts

for f in tests/e2e/*.py; do
  echo "Collecting nodes from $f"
  nodes_raw=$(pytest -q --collect-only "$f" 2>/dev/null || true)
  mapfile -t nodes < <(printf "%s\n" "$nodes_raw" | grep "::" || true)
  if [ ${#nodes[@]} -eq 0 ]; then
    echo "No nodes in $f"
    continue
  fi

  for node in "${nodes[@]}"; do
    node_trim=$(printf "%s" "$node" | sed -e 's/^[[:space:]]*//;s/[[:space:]]*$//')
    echo "-> Running node: $node_trim"
    pkill -f playwright || true
    sleep 1
    safe_name=$(printf "%s" "$node_trim" | tr -c '[:alnum:]' '_')
    logfile="tests/e2e/logs/individual_node_runs/$(basename "$f").$safe_name.log"

    python -m pytest "$node_trim" -q -s | tee "$logfile"
    rc=${PIPESTATUS[0]}
    if [ $rc -ne 0 ]; then
      echo "FAIL: $node_trim rc=$rc, logs at $logfile"
      ts=$(date -u +%Y%m%dT%H%M%SZ)
      mkdir -p "tests/e2e/logs/full_run_artifacts/failure_$ts"
      find . -type d -name 'playwright-report' -exec cp -r {} "tests/e2e/logs/full_run_artifacts/failure_$ts" \; || true
      find . -type f \( -name '*.png' -o -name '*.zip' -o -name '*.html' -o -name '*.har' -o -name '*.json' \) -exec cp --parents {} "tests/e2e/logs/full_run_artifacts/failure_$ts" \; || true
      echo "Artifacts copied to tests/e2e/logs/full_run_artifacts/failure_$ts"
      exit $rc
    fi
    echo "PASS: $node_trim"
    sleep 1
  done
  echo "Completed nodes in $f"
done

# Full suite pass
echo "All node runs completed; running full suite now"
pkill -f playwright || true
sleep 2
python -m pytest tests/e2e/ -q -s -p no:helpconfig | tee tests/e2e/logs/full_suite_run.log
rc=${PIPESTATUS[0]}
if [ $rc -ne 0 ]; then
  echo "Full suite failed (rc=$rc); collecting artifacts"
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  mkdir -p "tests/e2e/logs/full_run_artifacts/failure_$ts"
  find . -type d -name 'playwright-report' -exec cp -r {} "tests/e2e/logs/full_run_artifacts/failure_$ts" \; || true
  find . -type f \( -name '*.png' -o -name '*.zip' -o -name '*.html' -o -name '*.har' -o -name '*.json' \) -exec cp --parents {} "tests/e2e/logs/full_run_artifacts/failure_$ts" \; || true
  echo "Artifacts copied to tests/e2e/logs/full_run_artifacts/failure_$ts"
  exit $rc
fi

echo "Full E2E suite passed"
