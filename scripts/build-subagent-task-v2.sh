#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 \"<task description>\"" >&2
  exit 1
fi

python3 /Users/fx/.openclaw/workspace/skills/task-notify/scripts/build-subagent-task.py "$*"
