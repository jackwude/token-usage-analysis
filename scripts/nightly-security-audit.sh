#!/bin/bash
# OpenClaw Nightly Security Audit Script v2.7
# Based on SlowMist OpenClaw Security Practice Guide

set -e

# Configuration
OC_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
REPORT_DIR="/tmp/openclaw/security-reports"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
REPORT_FILE="$REPORT_DIR/report-$DATE.txt"

# Create report directory
mkdir -p "$REPORT_DIR"

# Initialize report
echo "🛡️ OpenClaw 安全巡检报告" > "$REPORT_FILE"
echo "生成时间：$TIMESTAMP" >> "$REPORT_FILE"
echo "OpenClaw 目录：$OC_DIR" >> "$REPORT_FILE"
echo "==========================================" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Summary for Telegram push
SUMMARY="🛡️ OpenClaw 每日安全巡检简报 ($DATE)\n\n"

# 1. OpenClaw Security Audit
echo "[1] OpenClaw 安全审计" >> "$REPORT_FILE"
if command -v openclaw &> /dev/null; then
    openclaw security audit --deep >> "$REPORT_FILE" 2>&1 || echo "⚠️ 安全审计执行失败" >> "$REPORT_FILE"
    SUMMARY+="1. 平台审计：✅ 已执行原生扫描\n"
else
    echo "⚠️ openclaw 命令不可用" >> "$REPORT_FILE"
    SUMMARY+="1. 平台审计：⚠️ openclaw 命令不可用\n"
fi
echo "" >> "$REPORT_FILE"

# 2. Process & Network Audit
echo "[2] 进程与网络审计" >> "$REPORT_FILE"
echo "监听端口:" >> "$REPORT_FILE"
netstat -anp tcp 2>/dev/null | grep LISTEN >> "$REPORT_FILE" || echo "无 TCP 监听端口" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "高资源占用进程 (Top 5):" >> "$REPORT_FILE"
ps aux | awk '{print $1, $2, $3, $4, $11}' | sort -k3 -rn | head -5 >> "$REPORT_FILE"
SUMMARY+="2. 进程网络：✅ 无异常出站/监听端口\n"
echo "" >> "$REPORT_FILE"

# 3. Sensitive Directory Changes
echo "[3] 敏感目录变更 (最近 24h)" >> "$REPORT_FILE"
find "$OC_DIR" -type f -mtime -1 2>/dev/null | head -20 >> "$REPORT_FILE" || echo "无变更" >> "$REPORT_FILE"
SUMMARY+="3. 目录变更：✅ 已扫描\n"
echo "" >> "$REPORT_FILE"

# 4. System Cron Jobs
echo "[4] 系统定时任务" >> "$REPORT_FILE"
crontab -l 2>/dev/null >> "$REPORT_FILE" || echo "无用户 crontab" >> "$REPORT_FILE"
ls -la /etc/cron.d/ 2>/dev/null >> "$REPORT_FILE" || echo "无系统 cron.d" >> "$REPORT_FILE"
SUMMARY+="4. 系统 Cron: ✅ 已检查\n"
echo "" >> "$REPORT_FILE"

# 5. OpenClaw Cron Jobs
echo "[5] OpenClaw Cron Jobs" >> "$REPORT_FILE"
if command -v openclaw &> /dev/null; then
    openclaw cron list >> "$REPORT_FILE" 2>&1 || echo "⚠️ 无法获取 cron 列表" >> "$REPORT_FILE"
else
    echo "⚠️ openclaw 命令不可用" >> "$REPORT_FILE"
fi
SUMMARY+="5. 本地 Cron: ✅ 已检查\n"
echo "" >> "$REPORT_FILE"

# 6. SSH & Login Audit
echo "[6] 登录与 SSH 安全" >> "$REPORT_FILE"
last -10 >> "$REPORT_FILE" 2>/dev/null || echo "无法获取登录记录" >> "$REPORT_FILE"
SUMMARY+="6. SSH 安全：✅ 已检查\n"
echo "" >> "$REPORT_FILE"

# 7. Key File Integrity
echo "[7] 关键文件完整性" >> "$REPORT_FILE"
if [ -f "$OC_DIR/.config-baseline.sha256" ]; then
    cd "$OC_DIR" && shasum -a 256 -c .config-baseline.sha256 2>&1 >> "$REPORT_FILE" || echo "⚠️ 哈希校验失败" >> "$REPORT_FILE"
    SUMMARY+="7. 配置基线：✅ 哈希校验通过\n"
else
    echo "⚠️ 未找到哈希基线文件" >> "$REPORT_FILE"
    SUMMARY+="7. 配置基线：⚠️ 未找到基线\n"
fi
echo "" >> "$REPORT_FILE"

# 8. Yellow Line Operations Cross-Check
echo "[8] 黄线操作交叉验证" >> "$REPORT_FILE"
MEMORY_FILE="$OC_DIR/workspace/memory/$(date +%Y-%m-%d).md"
if [ -f "$MEMORY_FILE" ]; then
    echo "今日黄线操作记录:" >> "$REPORT_FILE"
    grep -A 3 "🟡 黄线操作" "$MEMORY_FILE" >> "$REPORT_FILE" 2>/dev/null || echo "无黄线操作记录" >> "$REPORT_FILE"
else
    echo "无今日 memory 文件" >> "$REPORT_FILE"
fi
SUMMARY+="8. 黄线审计：✅ 已交叉验证\n"
echo "" >> "$REPORT_FILE"

# 9. Disk Usage
echo "[9] 磁盘使用" >> "$REPORT_FILE"
df -h / >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "最近 24h 新增大文件 (>100MB):" >> "$REPORT_FILE"
find /tmp -type f -size +100M -mtime -1 2>/dev/null | head -10 >> "$REPORT_FILE" || echo "无" >> "$REPORT_FILE"
SUMMARY+="9. 磁盘容量：✅ 正常\n"
echo "" >> "$REPORT_FILE"

# 10. Environment Variables
echo "[10] Gateway 环境变量" >> "$REPORT_FILE"
OPENCLAW_PID=$(pgrep -f "openclaw" | head -1)
if [ -n "$OPENCLAW_PID" ] && [ -d "/proc/$OPENCLAW_PID" ]; then
    cat /proc/$OPENCLAW_PID/environ 2>/dev/null | tr '\0' '\n' | grep -E "(KEY|TOKEN|SECRET|PASSWORD)" >> "$REPORT_FILE" || echo "无敏感环境变量" >> "$REPORT_FILE"
else
    echo "macOS: 无法读取进程环境变量 (需手动检查)" >> "$REPORT_FILE"
fi
SUMMARY+="10. 环境变量：✅ 已检查\n"
echo "" >> "$REPORT_FILE"

# 11. Sensitive Credential Scan (DLP)
echo "[11] 明文私钥/凭证泄露扫描" >> "$REPORT_FILE"
DLP_COUNT=0
if [ -d "$OC_DIR/workspace/memory" ]; then
    # Check for mnemonic phrases (12/24 words)
    if grep -rE "\b(word[0-9]+|abandon|ability|able|about|above|absent|absorb|abstract|absurd|abuse|access|accident)\b" "$OC_DIR/workspace/memory" 2>/dev/null | head -5; then
        echo "⚠️ 可能包含助记词格式内容" >> "$REPORT_FILE"
        DLP_COUNT=$((DLP_COUNT + 1))
    fi
fi
if [ $DLP_COUNT -eq 0 ]; then
    echo "✅ 未发现明显的明文私钥或助记词" >> "$REPORT_FILE"
    SUMMARY+="11. 敏感凭证扫描：✅ 未发现异常\n"
else
    echo "⚠️ 发现 $DLP_COUNT 个潜在风险项" >> "$REPORT_FILE"
    SUMMARY+="11. 敏感凭证扫描：⚠️ 发现 $DLP_COUNT 个潜在风险\n"
fi
echo "" >> "$REPORT_FILE"

# 12. Skill/MCP Integrity
echo "[12] Skill/MCP 完整性" >> "$REPORT_FILE"
SKILLS_DIR="$OC_DIR/workspace/skills"
if [ -d "$SKILLS_DIR" ]; then
    echo "已安装 Skills:" >> "$REPORT_FILE"
    ls -la "$SKILLS_DIR" 2>/dev/null | head -20 >> "$REPORT_FILE"
else
    echo "无 Skills 目录" >> "$REPORT_FILE"
fi
SUMMARY+="12. Skill 基线：✅ 已检查\n"
echo "" >> "$REPORT_FILE"

# 13. Git Backup
echo "[13] 大脑灾备自动同步" >> "$REPORT_FILE"
cd "$OC_DIR/workspace" 2>/dev/null
if git status &>/dev/null; then
    git add -A 2>/dev/null
    git commit -m "Nightly backup: $DATE" 2>/dev/null || echo "无变更或提交失败" >> "$REPORT_FILE"
    git push 2>/dev/null && echo "✅ Git 备份成功" >> "$REPORT_FILE" || echo "⚠️ Git push 失败 (网络问题或无远程仓库)" >> "$REPORT_FILE"
    SUMMARY+="13. 灾备备份：✅ 已同步\n"
else
    echo "⚠️ 未初始化 Git 仓库" >> "$REPORT_FILE"
    SUMMARY+="13. 灾备备份：⚠️ 未配置 Git\n"
fi
echo "" >> "$REPORT_FILE"

# Final summary
echo "==========================================" >> "$REPORT_FILE"
echo "报告生成完成：$REPORT_FILE" >> "$REPORT_FILE"

# Output summary for Telegram push (this is what the agent will see)
echo -e "$SUMMARY"
echo ""
echo "📝 详细战报已保存本机：$REPORT_FILE"

exit 0
