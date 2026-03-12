#!/usr/bin/env bash
set -euo pipefail

# SpeedCat checkin + usage (Agent Browser state-first)
# Output: fixed template to stdout.

node "$(cd "$(dirname "$0")" && pwd)/run.js"
