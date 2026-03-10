#!/bin/bash
# Token 用量分析 - 快捷命令
# 用法：
#   token-usage                  # 交互式选择时间范围
#   token-usage 24h              # 过去 24 小时
#   token-usage 7d               # 过去 7 天
#   token-usage 30d              # 过去 30 天
#   token-usage weekend          # 上周末
#   token-usage last_week        # 上周
#   token-usage custom 2026-03-07 2026-03-08  # 自定义日期

set -euo pipefail

ANALYZE_SCRIPT="$HOME/.openclaw/workspace/skills/token-usage-analysis/analyze_usage.py"

if [ ! -f "$ANALYZE_SCRIPT" ]; then
    echo "❌ 分析脚本不存在：$ANALYZE_SCRIPT"
    exit 1
fi

python3 "$ANALYZE_SCRIPT" "$@"
