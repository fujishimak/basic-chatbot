#!/usr/bin/env bash
# Tail startup logs for the OpenLIT + ClickHouse containers.
#
# Usage:
#   ./scripts/openlit-logs.sh            # show the last 60 lines of each (snapshot, exits)
#   ./scripts/openlit-logs.sh -f         # follow live (Ctrl+C to stop watching)
#   ./scripts/openlit-logs.sh -n 200     # show the last 200 lines of each
#   ./scripts/openlit-logs.sh -f -n 100  # follow, starting from the last 100 lines

set -euo pipefail

CONTAINERS=("clickhouse" "openlit")
TAIL=60
FOLLOW=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--follow) FOLLOW="-f"; shift ;;
    -n|--tail)   TAIL="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

for name in "${CONTAINERS[@]}"; do
  if ! podman container exists "$name"; then
    echo "WARNING: container '$name' not found (skipping)" >&2
    continue
  fi
  status=$(podman inspect -f '{{.State.Status}}' "$name" 2>/dev/null || echo "unknown")
  echo "==================================================================="
  echo "  $name  (status: $status)"
  echo "==================================================================="
  # --timestamps so we can see the ready-vs-started gap; --tail bounds the backlog.
  podman logs ${FOLLOW} --tail "$TAIL" --timestamps "$name" 2>&1 || true
  echo ""
done
