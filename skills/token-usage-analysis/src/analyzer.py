#!/usr/bin/env python3
"""
Token Usage Analysis Script
分析 OpenClaw Token 用量日志，支持多种时间范围选择
"""
import os, re, sys
from datetime import datetime, timedelta
from collections import defaultdict

log_path = os.path.expanduser('~/.openclaw/logs/session-usage.log')

# 匹配日志行（带 agent 字段的格式）
rx = re.compile(r'^(?P<ts>[^ ]+) \| agent=(?P<agent>[^ ]+) \| session=(?P<session>[^ ]+) \| model=(?P<model>[^ ]+) \| tokens_in=(?P<tin>\d+) \| tokens_out=(?P<tout>\d+) \| cost=\$(?P<cost>[0-9.]+) ')

def parse_iso(ts: str) -> datetime:
    """解析 ISO 时间戳，返回 naive datetime"""
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt

def get_time_range(choice: str) -> tuple:
    """根据用户选择返回时间范围 (start, end, label)"""
    now = datetime.now()
    
    if choice == '1' or choice == '24h':
        # 过去 24 小时
        start = now - timedelta(hours=24)
        label = "过去 24 小时"
        return (start, now, label)
    
    elif choice == '2' or choice == '7d':
        # 过去 7 天
        start = now - timedelta(days=7)
        label = "过去 7 天"
        return (start, now, label)
    
    elif choice == '3' or choice == '30d':
        # 过去 30 天
        start = now - timedelta(days=30)
        label = "过去 30 天"
        return (start, now, label)
    
    elif choice == '4' or choice == 'weekend':
        # 上周末（最近一个周六 + 周日）
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        weekday = today.weekday()  # 0=周一，6=周日
        
        if weekday == 6:  # 今天是周日，上周末是昨天 + 前天
            sun = today - timedelta(days=1)
            sat = today - timedelta(days=2)
        elif weekday == 5:  # 今天是周六，上周末是今天 + 昨天
            sun = today
            sat = today - timedelta(days=1)
        else:  # 周一到周五，上周末是上周六 + 周日
            sun = today - timedelta(days=(weekday + 1))
            sat = sun - timedelta(days=1)
        
        start = sat
        end = sun.replace(hour=23, minute=59, second=59)
        label = f"上周末 ({sat.strftime('%m/%d')} 周六 ~ {sun.strftime('%m/%d')} 周日)"
        return (start, end, label)
    
    elif choice == '5' or choice == 'last_week':
        # 上周（周一到周日）
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        weekday = today.weekday()
        
        # 本周一
        this_monday = today - timedelta(days=weekday)
        # 上周一
        last_monday = this_monday - timedelta(days=7)
        # 上周日
        last_sunday = last_monday + timedelta(days=6)
        
        start = last_monday
        end = last_sunday.replace(hour=23, minute=59, second=59)
        label = f"上周 ({last_monday.strftime('%m/%d')} ~ {last_sunday.strftime('%m/%d')})"
        return (start, end, label)
    
    elif choice == '6' or choice == 'custom':
        # 自定义日期范围（需要用户输入）
        print("请输入起始日期 (YYYY-MM-DD): ", end='')
        start_str = input().strip()
        print("请输入结束日期 (YYYY-MM-DD): ", end='')
        end_str = input().strip()
        
        try:
            start = datetime.strptime(start_str, '%Y-%m-%d')
            end = datetime.strptime(end_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            label = f"{start_str} ~ {end_str}"
            return (start, end, label)
        except ValueError as e:
            print(f"日期格式错误：{e}")
            sys.exit(1)
    
    else:
        print(f"未知选项：{choice}")
        sys.exit(1)

def analyze_usage(start: datetime, end: datetime, label: str) -> str:
    """分析指定时间范围内的用量数据，返回格式化报告"""
    
    if not os.path.exists(log_path):
        return f"❌ 日志文件不存在：{log_path}"
    
    # 按 (agent, session, date) 分组
    session_daily = defaultdict(list)
    
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            m = rx.match(line)
            if not m:
                continue
            
            ts = parse_iso(m['ts'])
            if ts < start or ts > end:
                continue
            
            agent = m['agent']
            session = m['session']
            tin = int(m['tin'])
            tout = int(m['tout'])
            cost = float(m['cost'])
            
            date_str = ts.strftime('%Y-%m-%d')
            session_daily[(agent, session, date_str)].append((ts, tin, tout, cost))
    
    # 计算每个 agent 每天的增量
    agent_daily = defaultdict(lambda: defaultdict(lambda: {'total_in': 0, 'total_out': 0, 'cost': 0.0, 'sessions': set()}))
    
    for (agent, session, date_str), snapshots in session_daily.items():
        if len(snapshots) < 2:
            continue
        
        snapshots.sort(key=lambda x: x[0])
        first = snapshots[0]
        last = snapshots[-1]
        
        delta_in = last[1] - first[1]
        delta_out = last[2] - first[2]
        delta_cost = last[3] - first[3]
        
        if delta_in < 0: delta_in = 0
        if delta_out < 0: delta_out = 0
        if delta_cost < 0: delta_cost = 0.0
        
        agent_daily[agent][date_str]['total_in'] += delta_in
        agent_daily[agent][date_str]['total_out'] += delta_out
        agent_daily[agent][date_str]['cost'] += delta_cost
        agent_daily[agent][date_str]['sessions'].add(session)
    
    # 生成报告
    lines = []
    lines.append("=" * 70)
    lines.append(f"🦞 Token 用量汇总分析（{label}）")
    lines.append("=" * 70)
    lines.append("")
    
    if not agent_daily:
        lines.append("⚠️  该时间段内没有检测到有效的用量增量数据")
        lines.append("   可能原因：")
        lines.append("   1. 日志记录在该时间段未运行")
        lines.append("   2. session 文件在该时间段没有变化")
        lines.append("   3. 时间范围选择错误")
        lines.append("")
        return "\n".join(lines)
    
    # 按 agent 输出
    grand_total_in = 0
    grand_total_out = 0
    grand_cost = 0.0
    all_sessions = set()
    
    for agent in sorted(agent_daily.keys()):
        daily_data = agent_daily[agent]
        lines.append(f"📊 Agent: {agent}")
        lines.append("-" * 60)
        
        weekend_total_in = 0
        weekend_total_out = 0
        weekend_cost = 0.0
        weekend_sessions = set()
        
        for date_str in sorted(daily_data.keys()):
            data = daily_data[date_str]
            total = data['total_in'] + data['total_out']
            session_count = len(data['sessions'])
            
            # 格式化日期显示（带星期）
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                weekday_map = ['一', '二', '三', '四', '五', '六', '日']
                date_display = f"{date_str} (周{weekday_map[date_obj.weekday()]})"
            except:
                date_display = date_str
            
            lines.append(f"  📅 {date_display}:")
            lines.append(f"     Token: {total:,} (in={data['total_in']:,}, out={data['total_out']:,})")
            lines.append(f"     Cost:  ${data['cost']:.4f}")
            lines.append(f"     Sessions: {session_count}")
            
            weekend_total_in += data['total_in']
            weekend_total_out += data['total_out']
            weekend_cost += data['cost']
            weekend_sessions.update(data['sessions'])
        
        lines.append("")
        lines.append(f"  📈 合计:")
        weekend_total = weekend_total_in + weekend_total_out
        lines.append(f"     Token: {weekend_total:,} (in={weekend_total_in:,}, out={weekend_total_out:,})")
        lines.append(f"     Cost:  ${weekend_cost:.4f}")
        lines.append(f"     Sessions: {len(weekend_sessions)}")
        lines.append("")
        
        grand_total_in += weekend_total_in
        grand_total_out += weekend_total_out
        grand_cost += weekend_cost
        all_sessions.update(weekend_sessions)
    
    # 总体汇总
    lines.append("=" * 70)
    lines.append("📊 总计（所有 Agent）")
    lines.append("-" * 60)
    
    grand_total = grand_total_in + grand_total_out
    lines.append(f"总 Token: {grand_total:,} (in={grand_total_in:,}, out={grand_total_out:,})")
    lines.append(f"总 Cost: ${grand_cost:.4f}")
    lines.append(f"总 Sessions: {len(all_sessions)}")
    lines.append(f"Agent 数量：{len(agent_daily)}")
    
    # 用量分布
    if len(agent_daily) > 1:
        lines.append("")
        lines.append("💡 用量分布:")
        # 先计算每个 agent 的总量，再排序
        agent_totals = []
        for agent in agent_daily.keys():
            agent_total = sum(d['total_in'] + d['total_out'] for d in agent_daily[agent].values())
            agent_totals.append((agent, agent_total))
        agent_totals.sort(key=lambda x: x[1], reverse=True)
        
        for agent, agent_total in agent_totals:
            percentage = (agent_total / grand_total * 100) if grand_total > 0 else 0
            lines.append(f"- {agent}: {percentage:.1f}%")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)

def print_menu():
    """打印时间范围选择菜单"""
    print("""
请选择时间范围：
1. 过去 24 小时
2. 过去 7 天
3. 过去 30 天
4. 上周末（最近一个周六 + 周日）
5. 上周（周一到周日）
6. 自定义日期范围

请输入选项编号 (1-6): """, end='')

if __name__ == '__main__':
    # 检查是否通过命令行参数指定时间范围
    if len(sys.argv) > 1:
        choice = sys.argv[1]
        if choice == 'custom' and len(sys.argv) >= 4:
            # 命令行自定义：python analyze_usage.py custom 2026-03-07 2026-03-08
            start_str = sys.argv[2]
            end_str = sys.argv[3]
            try:
                start = datetime.strptime(start_str, '%Y-%m-%d')
                end = datetime.strptime(end_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                label = f"{start_str} ~ {end_str}"
                print(analyze_usage(start, end, label))
                sys.exit(0)
            except ValueError as e:
                print(f"日期格式错误：{e}")
                sys.exit(1)
        else:
            start, end, label = get_time_range(choice)
            print(analyze_usage(start, end, label))
    else:
        # 交互式模式
        print_menu()
        choice = input().strip()
        start, end, label = get_time_range(choice)
        print(analyze_usage(start, end, label))
