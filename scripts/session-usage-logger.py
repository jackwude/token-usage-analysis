#!/usr/bin/env python3
"""
OpenClaw Session Usage Logger
记录当前 session 的 usage 状态到日志文件
"""

import json
import os
import subprocess
from datetime import datetime

LOG_FILE = os.path.expanduser("~/.openclaw/logs/session-usage.log")
MAX_SIZE = 10 * 1024 * 1024  # 10MB

def check_log_size():
    """检查日志文件大小，超过 10MB 返回 True"""
    if not os.path.exists(LOG_FILE):
        return False
    return os.path.getsize(LOG_FILE) >= MAX_SIZE

def get_session_data():
    """通过 sessions_list 获取 session 数据"""
    try:
        # 读取 sessions_list 的输出（通过 openclaw CLI）
        result = subprocess.run(
            ["node", "-e", """
const fs = require('fs');
const path = require('path');

// 读取当前活跃 session 的信息
const sessionsDir = path.join(os.homedir(), '.openclaw', 'agents', 'main', 'sessions');
const sessions = [];

try {
  const files = fs.readdirSync(sessionsDir).filter(f => f.endsWith('.jsonl'));
  for (const f of files) {
    const stat = fs.statSync(path.join(sessionsDir, f));
    const mtime = new Date(stat.mtime);
    // 只取最近 2 小时内活跃的
    if (Date.now() - mtime.getTime() < 2 * 3600 * 1000) {
      sessions.push({
        id: f.replace('.jsonl', ''),
        mtime: mtime.toISOString()
      });
    }
  }
} catch(e) {}

console.log(JSON.stringify({sessions}));
            """],
            capture_output=True,
            text=True,
            timeout=10
        )
        return json.loads(result.stdout.strip())
    except Exception as e:
        return {"error": str(e), "sessions": []}

def main():
    # 检查是否需要提醒（达到 10MB）
    size_warning = check_log_size()
    
    # 获取 session 数据
    data = get_session_data()
    sessions = data.get("sessions", [])
    
    if not sessions:
        print("⚠️ 没有找到活跃的 session")
        return
    
    # 记录每个活跃 session
    timestamp = datetime.now().isoformat()
    logged = []
    
    for session in sessions:
        log_line = f"{timestamp} | session={session['id'][:36]} | active_at={session['mtime']}\n"
        logged.append(log_line.strip())
    
    # 写入日志
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for line in logged:
            f.write(line + "\n")
    
    # 输出结果
    for line in logged:
        print(f"✅ 已记录：{line}")
    
    if size_warning:
        print("\n⚠️ 警告：session-usage.log 已达到 10MB，需要清理！")

if __name__ == "__main__":
    main()
