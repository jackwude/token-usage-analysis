#!/usr/bin/env python3
"""
Token Usage Analysis Script
分析 OpenClaw Token 用量日志，按固定模板输出结果。
"""
import os
import re
import sys
from datetime import datetime, timedelta
from collections import defaultdict

log_path = os.path.expanduser('~/.openclaw/logs/session-usage.log')

# 匹配日志行（带 agent 字段的格式）
rx = re.compile(
    r'^(?P<ts>[^ ]+) \| agent=(?P<agent>[^ ]+) \| session=(?P<session>[^ ]+) '
    r'\| model=(?P<model>[^ ]+) \| tokens_in=(?P<tin>\d+) \| tokens_out=(?P<tout>\d+) '
    r'\| cost=\$(?P<cost>[0-9.]+) '
)


def parse_iso(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


def get_time_range(choice: str) -> tuple:
    now = datetime.now()

    if choice == '1' or choice == '24h':
        start = now - timedelta(hours=24)
        label = "过去 24 小时"
        return (start, now, label)

    elif choice == '2' or choice == '7d':
        start = now - timedelta(days=7)
        label = "过去 7 天"
        return (start, now, label)

    elif choice == '3' or choice == '30d':
        start = now - timedelta(days=30)
        label = "过去 30 天"
        return (start, now, label)

    elif choice == '4' or choice == 'weekend':
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        weekday = today.weekday()

        if weekday == 6:
            sun = today - timedelta(days=1)
            sat = today - timedelta(days=2)
        elif weekday == 5:
            sun = today
            sat = today - timedelta(days=1)
        else:
            sun = today - timedelta(days=(weekday + 1))
            sat = sun - timedelta(days=1)

        start = sat
        end = sun.replace(hour=23, minute=59, second=59)
        label = f"上周末 ({sat.strftime('%m/%d')} 周六 ~ {sun.strftime('%m/%d')} 周日)"
        return (start, end, label)

    elif choice == '5' or choice == 'last_week':
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        weekday = today.weekday()
        this_monday = today - timedelta(days=weekday)
        last_monday = this_monday - timedelta(days=7)
        last_sunday = last_monday + timedelta(days=6)

        start = last_monday
        end = last_sunday.replace(hour=23, minute=59, second=59)
        label = f"上周 ({last_monday.strftime('%m/%d')} ~ {last_sunday.strftime('%m/%d')})"
        return (start, end, label)

    elif choice == '6' or choice == 'custom':
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


def collect_usage(start: datetime, end: datetime):
    if not os.path.exists(log_path):
        return None, f"❌ 日志文件不存在：{log_path}"

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

    agent_daily = defaultdict(lambda: defaultdict(lambda: {
        'total_in': 0,
        'total_out': 0,
        'cost': 0.0,
        'sessions': set(),
    }))

    raw_cost_daily = defaultdict(float)
    raw_cost_agent = defaultdict(float)
    raw_cost_total = 0.0

    for snapshots in session_daily.values():
        for _, _, _, cost in snapshots:
            raw_cost_total += cost

    for (agent, _session, date_str), snapshots in session_daily.items():
        day_snapshot_cost = sum(item[3] for item in snapshots)
        raw_cost_daily[date_str] += day_snapshot_cost
        raw_cost_agent[agent] += day_snapshot_cost

        if len(snapshots) < 2:
            continue

        snapshots.sort(key=lambda x: x[0])
        first = snapshots[0]
        last = snapshots[-1]

        delta_in = max(0, last[1] - first[1])
        delta_out = max(0, last[2] - first[2])
        delta_cost = max(0.0, last[3] - first[3])

        agent_daily[agent][date_str]['total_in'] += delta_in
        agent_daily[agent][date_str]['total_out'] += delta_out
        agent_daily[agent][date_str]['cost'] += delta_cost
        agent_daily[agent][date_str]['sessions'].add(_session)

    if not agent_daily and raw_cost_total <= 0:
        return None, "⚠️ 该时间段内没有检测到有效的用量数据"

    return {
        'agent_daily': agent_daily,
        'raw_cost_daily': raw_cost_daily,
        'raw_cost_agent': raw_cost_agent,
        'raw_cost_total': raw_cost_total,
    }, None


def fmt_million(n: int) -> str:
    return f"{n / 1_000_000:.2f}M"


def build_trend_lines(daily_totals: dict) -> list:
    if not daily_totals:
        return ["- 无数据"]

    max_total = max(daily_totals.values()) if daily_totals else 0
    lines = []
    for date_str in sorted(daily_totals.keys()):
        total = daily_totals[date_str]
        label = date_str[5:]
        if max_total <= 0:
            bar = "█"
        else:
            bar_len = max(1, round(total / max_total * 32)) if total > 0 else 1
            bar = "█" * bar_len
        lines.append(f"{label} | {bar} {fmt_million(total)}")
    return lines


def build_observations(agent_totals: dict, daily_totals: dict, peak_date: str, anomalies: list) -> list:
    observations = []

    grand_total = sum(agent_totals.values())
    if agent_totals and grand_total > 0:
        top_agent, top_total = max(agent_totals.items(), key=lambda x: x[1])
        pct = top_total / grand_total * 100
        observations.append(f"用量主要集中在 {top_agent}（{pct:.1f}%）")

    if peak_date and peak_date in daily_totals:
        observations.append(f"峰值出现在 {peak_date}（{fmt_million(daily_totals[peak_date])}）")

    if anomalies:
        observations.append(anomalies[0])
    else:
        observations.append("未发现明显异常波动")

    return observations[:2]


def build_one_liner(label: str, top_agent: str, peak_date: str, anomalies: list) -> str:
    if anomalies:
        return f"{label} 的用量主要集中在 {top_agent}，峰值在 {peak_date}，并存在异常信号，建议顺手核查。"
    return f"{label} 的用量主要集中在 {top_agent}，整体分布清晰，暂无明显异常。"


def analyze_usage(start: datetime, end: datetime, label: str) -> str:
    data, err = collect_usage(start, end)
    if err:
        return err

    agent_daily = data['agent_daily']

    agent_totals = {}
    agent_sessions = {}
    daily_totals = defaultdict(int)

    for agent, daily_map in agent_daily.items():
        total_in = sum(d['total_in'] for d in daily_map.values())
        total_out = sum(d['total_out'] for d in daily_map.values())
        sessions = set()
        for date_str, d in daily_map.items():
            day_total = d['total_in'] + d['total_out']
            daily_totals[date_str] += day_total
            sessions.update(d['sessions'])

        agent_totals[agent] = total_in + total_out
        agent_sessions[agent] = len(sessions)

    grand_total = sum(agent_totals.values())
    all_sessions = sum(agent_sessions.values())

    top_agent = max(agent_totals.items(), key=lambda x: x[1])[0] if agent_totals else "无"
    top_agent_pct = (agent_totals[top_agent] / grand_total * 100) if grand_total > 0 and top_agent != "无" else 0.0
    peak_date = max(daily_totals.items(), key=lambda x: x[1])[0] if daily_totals else "无"

    anomalies = []
    if grand_total == 0:
        anomalies.append("当前区间内未统计到 Token 增量")

    lines = []
    lines.append(f"📊 Token 用量分析（{label}）")
    lines.append("")
    lines.append("【结论】")
    lines.append(f"- 总 Token：{grand_total:,}")
    lines.append(f"- 主消耗 Agent：{top_agent}（{top_agent_pct:.1f}%）" if top_agent != "无" else "- 主消耗 Agent：无")
    lines.append(f"- 峰值日期：{peak_date}")
    lines.append(f"- 异常提示：{anomalies[0]}" if anomalies else "- 异常提示：无明显异常")
    lines.append("")
    lines.append("【Agent 明细】")

    if agent_totals:
        sorted_agents = sorted(agent_totals.items(), key=lambda x: x[1], reverse=True)
        for idx, (agent, token_total) in enumerate(sorted_agents, start=1):
            pct = (token_total / grand_total * 100) if grand_total > 0 else 0.0
            lines.append(f"{idx}. {agent}")
            lines.append(f"   - Token：{token_total:,}")
            lines.append(f"   - Sessions：{agent_sessions[agent]}")
            lines.append(f"   - 占比：{pct:.1f}%")
            lines.append("")
    else:
        lines.append("1. 无有效 Agent 数据")
        lines.append("   - Token：0")
        lines.append("   - Sessions：0")
        lines.append("   - 占比：0.0%")
        lines.append("")

    lines.append("【趋势图】")
    lines.extend(build_trend_lines(daily_totals))
    lines.append("")

    lines.append("【关键观察】")
    observations = build_observations(agent_totals, daily_totals, peak_date, anomalies)
    for item in observations:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("【一句话判断】")
    if anomalies:
        lines.append(f"{label} 的用量主要集中在 {top_agent}，峰值在 {peak_date}，并存在异常信号，建议顺手核查。")
    else:
        lines.append(f"{label} 的用量主要集中在 {top_agent}，整体分布清晰，暂无明显异常。")

    return "\n".join(lines)


def print_menu():
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
    if len(sys.argv) > 1:
        choice = sys.argv[1]
        if choice == 'custom' and len(sys.argv) >= 4:
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
        print_menu()
        choice = input().strip()
        start, end, label = get_time_range(choice)
        print(analyze_usage(start, end, label))
