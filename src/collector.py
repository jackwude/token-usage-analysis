#!/usr/bin/env python3
"""
Token Usage Collector
每小时收集 OpenClaw 各 Agent 的 Token 用量快照（增量统计）
"""
import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path

# 配置
LOG_DIR = Path.home() / ".openclaw" / "logs"
LOG_FILE = LOG_DIR / "session-usage.log"
STATE_FILE = LOG_DIR / "collector-state.json"
AGENTS_DIR = Path.home() / ".openclaw" / "agents"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
MAX_LOG_AGE_DAYS = 90  # 90 天

def rotate_log_if_needed():
    """日志轮转：超过 10MB 时压缩归档"""
    if not LOG_FILE.exists():
        return
    
    size = LOG_FILE.stat().st_size
    if size >= MAX_LOG_SIZE:
        # 轮转日志
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archived = LOG_FILE.parent / f"session-usage.log.{timestamp}"
        LOG_FILE.rename(archived)
        
        # 压缩归档
        import gzip
        with open(archived, 'rb') as f_in:
            with gzip.open(f"{archived}.gz", 'wb') as f_out:
                f_out.writelines(f_in)
        archived.unlink()
        
        print(f"📦 日志已轮转：{archived.name}.gz")

def cleanup_old_logs():
    """清理超过 90 天的日志"""
    if not LOG_DIR.exists():
        return
    
    import glob
    pattern = str(LOG_DIR / "session-usage.log.*.gz")
    for log_file in glob.glob(pattern):
        file_path = Path(log_file)
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        age_days = (datetime.now() - mtime).days
        
        if age_days > MAX_LOG_AGE_DAYS:
            file_path.unlink()
            print(f"🗑️ 已清理旧日志：{file_path.name} ({age_days}天前)")


def load_state():
    """加载状态文件（记录每个 session 上次收集的 token 累计值）"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_state(state):
    """保存状态文件"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def scan_session_file(session_file):
    """扫描 session 文件，返回累计 token 数和模型信息"""
    tokens_in = 0
    tokens_out = 0
    total_cost = 0.0
    model = "unknown"
    
    try:
        with open(session_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # 查找模型信息
            model_match = re.search(r'"modelId":"([^"]*)"', content)
            if not model_match:
                model_match = re.search(r'"model":"([^"]*)"', content)
            if model_match:
                model = model_match.group(1)
            
            # 累加所有 usage
            for line in content.split('\n'):
                if '"usage"' in line:
                    try:
                        data = json.loads(line)
                        usage = data.get('usage', {})
                        tokens_in += usage.get('input', 0)
                        tokens_out += usage.get('output', 0)
                        total_cost += usage.get('total', 0)
                    except json.JSONDecodeError:
                        # 降级：正则提取
                        input_match = re.search(r'"input":(\d+)', line)
                        output_match = re.search(r'"output":(\d+)', line)
                        cost_match = re.search(r'"total":([0-9.]+)', line)
                        
                        if input_match:
                            tokens_in += int(input_match.group(1))
                        if output_match:
                            tokens_out += int(output_match.group(1))
                        if cost_match:
                            total_cost += float(cost_match.group(1))
    except Exception as e:
        print(f"⚠️ 读取文件失败 {session_file}: {e}", file=sys.stderr)
    
    return tokens_in, tokens_out, total_cost, model

def collect_usage():
    """收集当前所有活跃 session 的用量快照（增量统计）"""
    timestamp = datetime.now().isoformat()
    
    if not AGENTS_DIR.exists():
        print(f"⚠️ agents 目录不存在：{AGENTS_DIR}", file=sys.stderr)
        return
    
    # 确保日志目录存在
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 加载状态文件
    state = load_state()
    
    lines_written = 0
    sessions_processed = 0
    
    # 遍历所有 agent
    for agent_dir in AGENTS_DIR.iterdir():
        if not agent_dir.is_dir():
            continue
        
        agent_id = agent_dir.name
        sessions_dir = agent_dir / "sessions"
        
        if not sessions_dir.exists():
            continue
        
        # 找出最近 2 小时内修改过的 jsonl 文件
        for session_file in sessions_dir.glob("*.jsonl"):
            # 检查文件修改时间
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
            age_minutes = (datetime.now() - mtime).total_seconds() / 60
            
            if age_minutes > 120:
                continue
            
            session_id = session_file.stem
            state_key = f"{agent_id}:{session_id}"
            
            # 扫描 session 文件，获取当前累计值
            current_in, current_out, current_cost, model = scan_session_file(session_file)
            
            # 获取上次累计值
            last_state = state.get(state_key, {
                'tokens_in': 0,
                'tokens_out': 0,
                'cost': 0.0
            })
            
            # 计算增量
            delta_in = max(0, current_in - last_state.get('tokens_in', 0))
            delta_out = max(0, current_out - last_state.get('tokens_out', 0))
            delta_cost = max(0.0, current_cost - last_state.get('cost', 0.0))
            
            # 只有增量 > 0 才记录
            if delta_in > 0 or delta_out > 0:
                # 写入日志
                log_line = (
                    f"{timestamp} | agent={agent_id} | session={session_id} | "
                    f"model={model} | tokens_in={delta_in} | tokens_out={delta_out} | "
                    f"cost=${delta_cost:.4f} | file_mtime={mtime.isoformat()} | "
                    f"file_size={session_file.stat().st_size}\n"
                )
                
                with open(LOG_FILE, 'a', encoding='utf-8') as f:
                    f.write(log_line)
                
                lines_written += 1
            
            # 更新状态（无论是否有增量，都更新累计值）
            state[state_key] = {
                'tokens_in': current_in,
                'tokens_out': current_out,
                'cost': current_cost,
                'updated_at': timestamp
            }
            sessions_processed += 1
    
    # 保存状态文件
    save_state(state)
    
    print(f"✅ 已收集 {lines_written} 个 session 增量快照 ({timestamp}), 共处理 {sessions_processed} 个 session")

def diagnose():
    """诊断工具：检查收集器状态"""
    print("🔍 Token Usage Collector 诊断")
    print("=" * 60)
    
    # 检查日志文件
    if LOG_FILE.exists():
        size = LOG_FILE.stat().st_size
        size_mb = size / 1024 / 1024
        lines = sum(1 for _ in open(LOG_FILE, 'r', encoding='utf-8', errors='ignore'))
        print(f"✅ 日志文件：{LOG_FILE} ({size_mb:.2f}MB, {lines}行)")
    else:
        print(f"❌ 日志文件不存在：{LOG_FILE}")
    
    # 检查状态文件
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
            print(f"✅ 状态文件：{STATE_FILE} ({len(state)} 个 session)")
        except:
            print(f"⚠️ 状态文件：{STATE_FILE} (读取失败)")
    else:
        print(f"ℹ️ 状态文件：{STATE_FILE} (首次运行将创建)")
    
    # 检查 agents 目录
    if AGENTS_DIR.exists():
        agents = list(AGENTS_DIR.iterdir())
        print(f"✅ Agents 目录：{len(agents)} 个 agent")
    else:
        print(f"❌ Agents 目录不存在：{AGENTS_DIR}")
    
    # 检查定时任务（macOS）
    import subprocess
    try:
        result = subprocess.run(
            ['launchctl', 'list', 'com.token-usage.collector'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print("✅ 定时任务：已配置 (launchd)")
        else:
            print("⚠️ 定时任务：未运行")
    except:
        print("⚠️ 定时任务：无法检测")
    
    # 检查最后执行时间
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                last_line = None
                for line in f:
                    if line.strip():
                        last_line = line
                
                if last_line:
                    timestamp = last_line.split(' | ')[0]
                    print(f"✅ 最后收集：{timestamp}")
        except:
            pass
    
    print("=" * 60)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--diagnose':
            diagnose()
        elif sys.argv[1] == '--rotate':
            rotate_log_if_needed()
        elif sys.argv[1] == '--cleanup':
            cleanup_old_logs()
        else:
            print(f"未知参数：{sys.argv[1]}")
            print("用法：collect-usage [--diagnose|--rotate|--cleanup]")
            sys.exit(1)
    else:
        # 正常收集流程
        cleanup_old_logs()
        rotate_log_if_needed()
        collect_usage()
