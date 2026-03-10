#!/bin/bash
# longtask-run.sh
# A minimal wrapper to run a long command and emit local heartbeats to stdout.
# NOTE: This script does NOT send messages by itself. It is meant to be used by the agent
# (exec+process poll) to avoid silent periods and provide progress updates.
#
# Usage:
#   scripts/longtask-run.sh --interval 150 -- label "fetch big repo" -- <command...>
# Example:
#   scripts/longtask-run.sh --interval 150 -- label "build" -- make test

set -euo pipefail

INTERVAL=150
LABEL="task"

if [[ "${1:-}" == "--interval" ]]; then
  INTERVAL="$2"; shift 2
fi

if [[ "${1:-}" != "--" ]]; then
  # optional: label <text>
  if [[ "${1:-}" == "label" ]]; then
    LABEL="$2"; shift 2
  fi
fi

if [[ "${1:-}" != "--" ]]; then
  echo "Usage: $0 [--interval N] [label TEXT] -- <command...>" >&2
  exit 2
fi
shift

START_TS=$(date +%s)
START_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')

# Run command in background so we can heartbeat.
"$@" &
CMD_PID=$!

HB=0

# First line: start marker
echo "[longtask] start label=\"$LABEL\" pid=$CMD_PID at=\"$START_HUMAN\""

while kill -0 "$CMD_PID" 2>/dev/null; do
  sleep "$INTERVAL" || true
  if ! kill -0 "$CMD_PID" 2>/dev/null; then
    break
  fi
  NOW_TS=$(date +%s)
  ELAPSED=$((NOW_TS-START_TS))
  HB=$((HB+1))
  echo "[longtask] heartbeat #$HB label=\"$LABEL\" pid=$CMD_PID elapsed=${ELAPSED}s"
done

wait "$CMD_PID"
RC=$?
END_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')
NOW_TS=$(date +%s)
ELAPSED=$((NOW_TS-START_TS))

echo "[longtask] done label=\"$LABEL\" pid=$CMD_PID rc=$RC elapsed=${ELAPSED}s at=\"$END_HUMAN\""
exit "$RC"
