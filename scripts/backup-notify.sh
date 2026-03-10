#!/bin/bash
set -euo pipefail

WORKSPACE_DIR="$HOME/.openclaw/workspace"
ENABLED_FILE="$WORKSPACE_DIR/scripts/backup-notify.enabled"
LOG_FILE="$WORKSPACE_DIR/logs/backup.log"

if [ ! -f "$ENABLED_FILE" ]; then
  echo "（通知已关闭）"
  exit 0
fi

now_cn=$(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M')

if [ ! -f "$LOG_FILE" ]; then
  echo "🦞 备份通知 | $now_cn"
  echo
  echo "⚠️ 未找到备份日志：$LOG_FILE"
  echo "📝 请先检查备份脚本是否已运行"
  exit 0
fi

segment=$(python3 - <<'PY'
from pathlib import Path
p = Path.home()/'.openclaw'/'workspace'/'logs'/'backup.log'
lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
start = None
end = None
for i in range(len(lines)-1, -1, -1):
    if end is None and '=== 备份完成 ===' in lines[i]:
        end = i
    if '=== 开始备份 ===' in lines[i]:
        start = i
        break
if start is None:
    print('')
elif end is None or end < start:
    print('\n'.join(lines[start:]))
else:
    print('\n'.join(lines[start:end+1]))
PY
)

status_line="⚠️ 备份状态未知"
summary_line="📝 未能从日志判断结果"

if printf '%s\n' "$segment" | grep -q '✅ 备份成功（已脱敏推送）'; then
  status_line="✅ 备份成功"
  summary_line="📝 检测到改动，已完成脱敏推送"
elif printf '%s\n' "$segment" | grep -q '✅ 备份成功'; then
  status_line="✅ 备份成功"
  summary_line="📝 检测到改动，备份已完成"
elif printf '%s\n' "$segment" | grep -q '📝 没有改动，跳过备份'; then
  status_line="📝 无改动"
  summary_line="📝 工作区无变化，已跳过备份"
elif printf '%s\n' "$segment" | grep -q '📝 快照与远端一致（无变更），跳过提交'; then
  status_line="📝 无改动"
  summary_line="📝 快照与远端一致，未生成新提交"
elif printf '%s\n' "$segment" | grep -q '❌ 推送失败'; then
  status_line="⚠️ 备份失败"
  summary_line="📝 推送失败，可能是网络或认证问题"
fi

git_line=$(cd "$WORKSPACE_DIR" && git status -sb | head -n 1)
if printf '%s' "$git_line" | grep -q 'ahead '; then
  ahead=$(printf '%s' "$git_line" | sed -nE 's/.*ahead ([0-9]+).*/\1/p')
  git_summary="⚠️ Git 未同步：本地领先 origin/main ${ahead} 个提交"
elif printf '%s' "$git_line" | grep -q 'behind '; then
  behind=$(printf '%s' "$git_line" | sed -nE 's/.*behind ([0-9]+).*/\1/p')
  git_summary="⚠️ Git 未同步：本地落后 origin/main ${behind} 个提交"
elif printf '%s' "$git_line" | grep -q '\[ahead .*behind '; then
  git_summary="⚠️ Git 未同步：本地与 origin/main 存在分叉"
else
  git_summary="✅ Git 同步正常：本地与 origin/main 一致"
fi

echo "🦞 备份通知 | $now_cn"
echo
echo "$status_line"
echo "$summary_line"
echo "$git_summary"
echo "📋 日志：~/.openclaw/workspace/logs/backup.log"
