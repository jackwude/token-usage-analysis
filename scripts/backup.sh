#!/bin/bash
# OpenClaw Workspace 自动备份脚本（GitHub）
# - 本地 workspace 可包含明文敏感信息
# - 备份时生成脱敏快照目录再提交/推送，避免敏感信息进入 Git 历史
#
# 每天凌晨 3 点执行（由 launchd 调用）

set -euo pipefail

WORKSPACE_DIR="$HOME/.openclaw/workspace"
SNAPSHOT_DIR="$HOME/.openclaw/workspace-snapshot"
LOG_FILE="$HOME/.openclaw/workspace/logs/backup.log"
NOTIFY_SNAPSHOT_FILE="$HOME/.openclaw/workspace/logs/backup-notify.last.txt"

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

refresh_notify_snapshot() {
  if [ -x "$WORKSPACE_DIR/scripts/backup-notify.sh" ]; then
    bash "$WORKSPACE_DIR/scripts/backup-notify.sh" > "$NOTIFY_SNAPSHOT_FILE" 2>/dev/null || true
  fi
}

trap refresh_notify_snapshot EXIT

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== 开始备份 ==="

# 仅当 workspace 有改动时才备份
cd "$WORKSPACE_DIR"
if ! git status --porcelain | grep -q .; then
  log "📝 没有改动，跳过备份"
  log "=== 备份完成 ==="
  exit 0
fi

log "检测到改动，准备生成脱敏快照..."

# 1) 准备快照仓库（clone / update）
if [ ! -d "$SNAPSHOT_DIR/.git" ]; then
  log "快照仓库不存在，开始 clone 到 $SNAPSHOT_DIR"
  mkdir -p "$SNAPSHOT_DIR"
  git clone --quiet "$(git remote get-url origin)" "$SNAPSHOT_DIR"
fi

cd "$SNAPSHOT_DIR"
# 尽量保持快照仓库在 origin/main 最新
git fetch --quiet origin main || true
git checkout --quiet main || true
git reset --hard --quiet origin/main || true

# 2) rsync workspace → snapshot（不带 .git）
log "同步文件到快照目录（rsync）"
rsync -a --delete \
  --exclude ".git" \
  --exclude ".DS_Store" \
  "$WORKSPACE_DIR/" "$SNAPSHOT_DIR/"

# 3) 脱敏规则
log "对快照进行脱敏处理"

# 3.1 TOOLS.md：遮盖常见“密码”字段（不改本地 workspace）
if [ -f "$SNAPSHOT_DIR/TOOLS.md" ]; then
  # 仅替换类似：- **密码**: xxxxx
  sed -E -i '' 's/^([[:space:]]*- \*\*密码\*\*:[[:space:]]*).+$/\1******/' "$SNAPSHOT_DIR/TOOLS.md" || true
fi

# 3.2 openclaw-config/openclaw.json：脱敏 token/key（按用户要求仍备份，但不上传明文）
if [ -f "$SNAPSHOT_DIR/openclaw-config/openclaw.json" ]; then
  python3 - <<'PY'
import json
from pathlib import Path

p = Path.home()/'.openclaw'/'workspace-snapshot'/'openclaw-config'/'openclaw.json'
obj = json.loads(p.read_text(encoding='utf-8'))

SENSITIVE_KEYS = {
  'apiKey', 'botToken', 'token', 'accessToken', 'refreshToken', 'secret',
  'password', 'pass', 'key', 'privateKey'
}

def scrub(x):
  if isinstance(x, dict):
    out = {}
    for k,v in x.items():
      if k in SENSITIVE_KEYS:
        out[k] = '******'
      else:
        out[k] = scrub(v)
    return out
  if isinstance(x, list):
    return [scrub(i) for i in x]
  return x

p.write_text(json.dumps(scrub(obj), ensure_ascii=False, indent=2) + "\n", encoding='utf-8')
PY
fi

# 4) 提交并推送
cd "$SNAPSHOT_DIR"
if git status --porcelain | grep -q .; then
  git add -A
  git commit -m "🤖 自动备份（脱敏快照）：$(date '+%Y-%m-%d %H:%M')" --quiet
  if git push origin main --quiet; then
    log "✅ 备份成功（已脱敏推送）"
  else
    log "❌ 推送失败，可能是网络问题或需要认证"
    exit 1
  fi
else
  log "📝 快照与远端一致（无变更），跳过提交"
fi

log "=== 备份完成 ==="
