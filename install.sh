#!/bin/bash
# Token Usage Analysis Skill - 安装脚本
# 自动配置定时任务，启用 Token 用量收集

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.openclaw/bin"
LOG_DIR="$HOME/.openclaw/logs"
SERVICES_DIR="$SKILL_DIR/services"

echo "🦞 Token Usage Analysis - 安装程序"
echo "=" * 60

# 1. 创建必要目录
echo "📁 创建目录..."
mkdir -p "$BIN_DIR"
mkdir -p "$LOG_DIR"

# 2. 安装可执行脚本
echo "🔧 安装可执行脚本..."
cp "$SKILL_DIR/src/collector.py" "$BIN_DIR/collect-usage"
cp "$SKILL_DIR/src/analyzer.py" "$BIN_DIR/analyze-usage" 2>/dev/null || true
chmod +x "$BIN_DIR/collect-usage"
chmod +x "$BIN_DIR/analyze-usage" 2>/dev/null || true

# 3. 检测操作系统并配置定时任务
OS=$(uname -s)
echo "💻 检测到操作系统：$OS"

if [ "$OS" = "Darwin" ]; then
    # macOS - 使用 launchd
    echo "⚙️  配置 macOS launchd 定时任务..."
    
    PLIST_FILE="$HOME/Library/LaunchAgents/com.token-usage.collector.plist"
    mkdir -p "$(dirname "$PLIST_FILE")"
    
    # 从模板创建 plist
    if [ -f "$SERVICES_DIR/com.token-usage.collector.plist" ]; then
        cp "$SERVICES_DIR/com.token-usage.collector.plist" "$PLIST_FILE"
    else
        # 内建模板（使用 $HOME 变量）
        cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.token-usage.collector</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-u</string>
        <string>$HOME/.openclaw/bin/collect-usage</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$HOME/.openclaw/logs/token-usage-collector.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.openclaw/logs/token-usage-collector.err</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF
    fi
    
    # 加载 launchd 任务
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    launchctl load "$PLIST_FILE"
    
    echo "✅ launchd 任务已配置：com.token-usage.collector"
    
elif [ "$OS" = "Linux" ]; then
    # Linux - 使用 cron
    echo "⚙️  配置 Linux cron 定时任务..."
    
    CRON_ENTRY="0 * * * * $BIN_DIR/collect-usage >> $LOG_DIR/token-usage-collector.log 2>&1"
    
    # 检查是否已存在
    if crontab -l 2>/dev/null | grep -q "token-usage"; then
        echo "⚠️  cron 任务已存在，跳过"
    else
        # 添加 cron 任务
        (crontab -l 2>/dev/null | grep -v "token-usage"; echo "$CRON_ENTRY") | crontab -
        echo "✅ cron 任务已配置（每小时执行）"
    fi
else
    echo "⚠️  未知操作系统，跳过定时任务配置"
    echo "   请手动配置定时任务，每小时执行：$BIN_DIR/collect-usage"
fi

# 4. 立即执行一次收集
echo "📊 执行首次日志收集..."
python3 "$BIN_DIR/collect-usage"

# 5. 写入安装状态
INSTALL_STATE="$SKILL_DIR/.installed"
cat > "$INSTALL_STATE" << EOF
installed_at=$(date -Iseconds)
os=$OS
version=1.1.0
EOF

echo ""
echo "=" * 60
echo "✅ 安装完成！"
echo ""
echo "📋 配置摘要:"
echo "   - 日志目录：$LOG_DIR"
echo "   - 收集脚本：$BIN_DIR/collect-usage"
echo "   - 定时任务：每小时执行（0 分）"
echo ""
echo "📊 使用说明:"
echo "   - 查询用量：说 '查 Token 用量'"
echo "   - 诊断状态：collect-usage --diagnose"
echo ""
echo "⏱️  提示：建议 24 小时后查询，获得完整的用量报告"
echo "=" * 60
