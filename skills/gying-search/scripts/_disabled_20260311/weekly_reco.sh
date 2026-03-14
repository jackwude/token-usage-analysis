#!/usr/bin/env bash
set -euo pipefail

bash ~/.openclaw/scripts/start-gying-chrome.sh >/dev/null 2>&1 || true

for _ in {1..20}; do
  if curl -fsS http://127.0.0.1:9224/json/version >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

node /Users/fx/.openclaw/workspace/skills/gying-search/scripts/weekly_reco.js
