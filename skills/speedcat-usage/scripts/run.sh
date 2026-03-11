#!/usr/bin/env bash
set -euo pipefail

# SpeedCat checkin + usage (CDP)
# Output: fixed template to stdout.

bash ~/.openclaw/scripts/start-speedcat-chrome.sh >/dev/null 2>&1 || true

node "$(cd "$(dirname "$0")" && pwd)/run.js"
