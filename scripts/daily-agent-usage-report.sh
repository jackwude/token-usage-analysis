#!/bin/bash
# 每天中午12点推送：过去24小时各 agent 的 token/cost 增量
set -euo pipefail

# 先写入一次最新快照（静默失败不阻断）
bash ~/.openclaw/workspace/scripts/global-session-usage-logger.sh >/dev/null 2>&1 || true

python3 ~/.openclaw/workspace/scripts/usage_24h_report.py | sed '1s/^/🦞 过去24小时各 Agent 消耗\n\n/'
