#!/bin/bash
# Token Usage Analysis Skill - 卸载脚本
# 移除定时任务，清理安装文件

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.openclaw/bin"

echo "🦞 Token Usage Analysis - 卸载程序"
echo "=" * 60

# 1. 移除定时任务
OS=$(uname -s)
echo "💻 检测到操作系统：$OS"

if [ "$OS" = "Darwin" ]; then
    # macOS - 移除 launchd 任务
    PLIST_FILE="$HOME/Library/LaunchAgents/com.token-usage.collector.plist"
    
    if [ -f "$PLIST_FILE" ]; then
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
        rm -f "$PLIST_FILE"
        echo "✅ launchd 任务已移除"
    else
        echo "⚠️  launchd 任务文件不存在"
    fi
    
elif [ "$OS" = "Linux" ]; then
    # Linux - 移除 cron 任务
    if crontab -l 2>/dev/null | grep -q "token-usage"; then
        crontab -l | grep -v "token-usage" | crontab -
        echo "✅ cron 任务已移除"
    else
        echo "⚠️  cron 任务不存在"
    fi
fi

# 2. 移除可执行脚本
echo "🔧 清理可执行脚本..."
rm -f "$BIN_DIR/collect-usage"
rm -f "$BIN_DIR/analyze-usage"
echo "✅ 可执行脚本已移除"

# 3. 移除安装状态
rm -f "$SKILL_DIR/.installed"

# 4. 询问是否保留日志数据
echo ""
echo "📁 日志文件处理:"
echo "   日志文件位于：$HOME/.openclaw/logs/session-usage.log"
echo ""
read -p "是否删除日志文件？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f "$HOME/.openclaw/logs/session-usage.log"
    rm -f "$HOME/.openclaw/logs/session-usage.log."*.gz
    echo "✅ 日志文件已删除"
else
    echo "ℹ️  日志文件已保留"
fi

echo ""
echo "=" * 60
echo "✅ 卸载完成！"
echo ""
echo "如需重新安装，运行："
echo "   $SKILL_DIR/install.sh"
echo "=" * 60
