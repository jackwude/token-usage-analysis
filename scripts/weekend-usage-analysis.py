#!/usr/bin/env python3
"""分析周末（3 月 7 日 -8 日）Token 用量，按 agent 分组统计"""
import os, re, sys
from datetime import datetime, timedelta
from collections import defaultdict

log_path = os.path.expanduser('~/.openclaw/logs/session-usage.log')
if not os.path.exists(log_path):
    print('日志不存在：', log_path)
    sys.exit(0)

# 匹配日志行（带 agent 字段的格式）
rx = re.compile(r'^(?P<ts>[^ ]+) \| agent=(?P<agent>[^ ]+) \| session=(?P<session>[^ ]+) \| model=(?P<model>[^ ]+) \| tokens_in=(?P<tin>\d+) \| tokens_out=(?P<tout>\d+) \| cost=\$(?P<cost>[0-9.]+) ')

def parse_iso(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    # 移除时区信息，转为 naive datetime 便于比较
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt

# 定义周末时间范围：3 月 7 日 00:00 到 3 月 8 日 23:59
start_sat = datetime(2026, 3, 7, 0, 0, 0)
end_sun = datetime(2026, 3, 8, 23, 59, 59)

# 按 (agent, session, date) 分组，记录每个 session 每天的快照
# 数据结构：{(agent, session, date): [(timestamp, tin, tout, cost), ...]}
session_daily = defaultdict(list)

with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        line = line.strip()
        m = rx.match(line)
        if not m:
            continue
        
        ts = parse_iso(m['ts'])
        # 只保留周末的数据
        if ts < start_sat or ts > end_sun:
            continue
        
        agent = m['agent']
        session = m['session']
        tin = int(m['tin'])
        tout = int(m['tout'])
        cost = float(m['cost'])
        
        # 按日期分组
        date_str = ts.strftime('%Y-%m-%d')
        session_daily[(agent, session, date_str)].append((ts, tin, tout, cost))

# 计算每个 agent 每天的增量
# 数据结构：{agent: {date: {total_tokens, cost, session_count}}}
agent_daily = defaultdict(lambda: defaultdict(lambda: {'total_in': 0, 'total_out': 0, 'cost': 0.0, 'sessions': set()}))

for (agent, session, date_str), snapshots in session_daily.items():
    if len(snapshots) < 2:
        # 只有一个快照，无法计算增量，跳过
        continue
    
    # 按时间排序
    snapshots.sort(key=lambda x: x[0])
    first = snapshots[0]
    last = snapshots[-1]
    
    # 计算增量
    delta_in = last[1] - first[1]
    delta_out = last[2] - first[2]
    delta_cost = last[3] - first[3]
    
    if delta_in < 0:
        delta_in = 0
    if delta_out < 0:
        delta_out = 0
    if delta_cost < 0:
        delta_cost = 0.0
    
    agent_daily[agent][date_str]['total_in'] += delta_in
    agent_daily[agent][date_str]['total_out'] += delta_out
    agent_daily[agent][date_str]['cost'] += delta_cost
    agent_daily[agent][date_str]['sessions'].add(session)

# 输出结果
print("=" * 70)
print("🦞 周末 Token 用量汇总分析（2026-03-07 周六 ~ 2026-03-08 周日）")
print("=" * 70)
print()

if not agent_daily:
    print("⚠️  周末期间没有检测到有效的用量增量数据")
    print("   可能原因：")
    print("   1. 日志记录在周末期间未运行")
    print("   2. session 文件在周末期间没有变化")
    print()
    sys.exit(0)

# 按 agent 排序输出
for agent in sorted(agent_daily.keys()):
    daily_data = agent_daily[agent]
    print(f"📊 Agent: {agent}")
    print("-" * 60)
    
    weekend_total_in = 0
    weekend_total_out = 0
    weekend_cost = 0.0
    weekend_sessions = set()
    
    for date_str in sorted(daily_data.keys()):
        data = daily_data[date_str]
        total = data['total_in'] + data['total_out']
        session_count = len(data['sessions'])
        
        print(f"  📅 {date_str}:")
        print(f"     Token: {total:,} (in={data['total_in']:,}, out={data['total_out']:,})")
        print(f"     Cost:  ${data['cost']:.4f}")
        print(f"     Sessions: {session_count}")
        
        weekend_total_in += data['total_in']
        weekend_total_out += data['total_out']
        weekend_cost += data['cost']
        weekend_sessions.update(data['sessions'])
    
    print()
    print(f"  📈 周末合计:")
    weekend_total = weekend_total_in + weekend_total_out
    print(f"     Token: {weekend_total:,} (in={weekend_total_in:,}, out={weekend_total_out:,})")
    print(f"     Cost:  ${weekend_cost:.4f}")
    print(f"     Sessions: {len(weekend_sessions)}")
    print()

# 总体汇总
print("=" * 70)
print("📊 周末总计（所有 Agent）")
print("-" * 60)

grand_total_in = 0
grand_total_out = 0
grand_cost = 0.0
all_sessions = set()

for agent in agent_daily:
    for date_str, data in agent_daily[agent].items():
        grand_total_in += data['total_in']
        grand_total_out += data['total_out']
        grand_cost += data['cost']
        all_sessions.update(data['sessions'])

grand_total = grand_total_in + grand_total_out
print(f"总 Token: {grand_total:,} (in={grand_total_in:,}, out={grand_total_out:,})")
print(f"总 Cost: ${grand_cost:.4f}")
print(f"总 Sessions: {len(all_sessions)}")
print(f"Agent 数量：{len(agent_daily)}")
print("=" * 70)
