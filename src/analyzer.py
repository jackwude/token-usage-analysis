#!/usr/bin/env python3
"""
Token Usage Analysis Script
分析 OpenClaw Token 用量日志，支持多种时间范围选择
"""
import os
import re
import sys
from datetime import datetime, timedelta
from collections import defaultdict

log_path = os.path.expanduser('~/.openclaw/logs/session-usage.log')

rx = re.compile(r'^(?P<ts>[^ ]+) \| agent=(?P<agent>[^ ]+) \| session=(?P<session>[^ ]+) \| model=(?P<model>[^ ]+) \| tokens_in=(?P<tin>\d+) \| tokens_out=(?P<tout>\d+) \| cost=\$(?P<cost>(?:[0-9.]+|NA)) ')


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


def format_millions(value: int) -> str:
    return f"{value / 1_000_000:.2f}M"


def build_bar_chart(date_totals, end: datetime, days: int = 7, width: int = 32):
    start_day = (end - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    points = []
    for i in range(days):
        day = start_day + timedelta(days=i)
        date_str = day.strftime('%Y-%m-%d')
        total = int(date_totals.get(date_str, 0))
        points.append((day.strftime('%m-%d'), total))

    max_total = max((total for _, total in points), default=0)
    lines = []
    for label, total in points:
        if max_total <= 0 or total <= 0:
            bar = '▏'
        else:
            bar_len = max(1, round(total / max_total * width))
            bar = '█' * bar_len
        lines.append(f"{label} | {bar} {format_millions(total)}")
    return lines


def build_observations(agent_summary, peak_date, peak_date_total, cost_anomalies):
    observations = []
    if agent_summary:
        top_agent = agent_summary[0]
        observations.append(f"用量高度集中在 {top_agent['agent']}（{top_agent['share']:.1f}%）")
    if peak_date:
        observations.append(f"峰值日期是 {peak_date}，单日消耗 {peak_date_total:,} Token")
    if cost_anomalies:
        observations.append(f"发现成本异常：{cost_anomalies[0]}")
    elif len(agent_summary) > 1:
        second_agent = agent_summary[1]
        observations.append(f"第二名是 {second_agent['agent']}，占比 {second_agent['share']:.1f}%")
    else:
        observations.append("当前用量主要由单一 Agent 构成")
    return observations[:3]


def build_judgement(agent_summary, peak_date, cost_anomalies):
    if not agent_summary:
        return "当前时间范围内没有足够数据，暂时无法判断整体消耗模式。"
    top_agent = agent_summary[0]['agent']
    if cost_anomalies:
        return f"该时间段属于 {top_agent} 主导的消耗模式，且存在成本异常，建议优先排查 cost 口径。"
    if peak_date:
        return f"该时间段属于 {top_agent} 主导的集中消耗模式，峰值出现在 {peak_date}。"
    return f"该时间段的 Token 消耗主要由 {top_agent} 驱动。"


def analyze_usage(start: datetime, end: datetime, label: str) -> str:
    if not os.path.exists(log_path):
        return f"❌ 日志文件不存在：{log_path}"

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
            cost = None if m['cost'] == 'NA' else float(m['cost'])
            date_str = ts.strftime('%Y-%m-%d')
            session_daily[(agent, session, date_str)].append((ts, tin, tout, cost))

    agent_daily = defaultdict(lambda: defaultdict(lambda: {'total_in': 0, 'total_out': 0, 'cost': 0.0, 'sessions': set(), 'cost_known': False}))

    for (agent, session, date_str), snapshots in session_daily.items():
        if len(snapshots) < 2:
            continue
        snapshots.sort(key=lambda x: x[0])
        first = snapshots[0]
        last = snapshots[-1]
        delta_in = max(last[1] - first[1], 0)
        delta_out = max(last[2] - first[2], 0)
        if first[3] is not None and last[3] is not None:
            delta_cost = max(last[3] - first[3], 0.0)
            agent_daily[agent][date_str]['cost'] += delta_cost
            agent_daily[agent][date_str]['cost_known'] = True
        agent_daily[agent][date_str]['total_in'] += delta_in
        agent_daily[agent][date_str]['total_out'] += delta_out
        agent_daily[agent][date_str]['sessions'].add(session)

    if not agent_daily:
        return (
            f"📊 Token 用量分析（{label}）\n\n"
            f"【结论】\n"
            f"- 总 Token：0\n"
            f"- 总 Cost：不可用\n"
            f"- 主消耗 Agent：无\n"
            f"- 峰值日期：无\n"
            f"- 异常提示：无明显异常\n\n"
            f"【Agent 明细】\n"
            f"- 当前时间范围内没有检测到有效数据\n\n"
            f"【7 天趋势图】\n"
            f"- 暂无趋势数据\n\n"
            f"【关键观察】\n"
            f"- 该时间段内没有检测到有效的用量增量数据\n"
            f"- 可能是日志未运行、session 无变化，或时间范围过窄\n"
            f"- 建议换更大的时间范围再试\n\n"
            f"【一句话判断】\n"
            f"当前时间范围内暂无可用分析结果。"
        )

    agent_summary = []
    date_totals = defaultdict(int)
    date_costs = defaultdict(float)
    date_cost_known = defaultdict(bool)
    grand_total_in = 0
    grand_total_out = 0
    grand_cost = 0.0
    any_cost_known = False

    for agent in sorted(agent_daily.keys()):
        total_in = 0
        total_out = 0
        total_cost = 0.0
        cost_known = False
        sessions = set()
        for date_str, data in agent_daily[agent].items():
            total_in += data['total_in']
            total_out += data['total_out']
            total_cost += data['cost']
            cost_known = cost_known or data['cost_known']
            sessions.update(data['sessions'])
            day_total = data['total_in'] + data['total_out']
            date_totals[date_str] += day_total
            if data['cost_known']:
                date_costs[date_str] += data['cost']
                date_cost_known[date_str] = True
        total = total_in + total_out
        grand_total_in += total_in
        grand_total_out += total_out
        grand_cost += total_cost
        any_cost_known = any_cost_known or cost_known
        agent_summary.append({
            'agent': agent,
            'token': total,
            'cost': total_cost,
            'cost_known': cost_known,
            'sessions': len(sessions),
            'share': 0.0,
        })

    grand_total = grand_total_in + grand_total_out
    for item in agent_summary:
        item['share'] = (item['token'] / grand_total * 100) if grand_total > 0 else 0.0
    agent_summary.sort(key=lambda x: x['token'], reverse=True)

    top_agent_text = "无"
    if agent_summary:
        top_agent_text = f"{agent_summary[0]['agent']}（{agent_summary[0]['share']:.1f}%）"

    peak_date = None
    peak_date_total = 0
    if date_totals:
        peak_date, peak_date_total = max(date_totals.items(), key=lambda x: x[1])

    cost_anomalies = []
    for date_str in sorted(date_totals.keys()):
        total = date_totals[date_str]
        if not date_cost_known.get(date_str):
            continue
        cost = date_costs[date_str]
        if total > 0 and cost / total > 0.0001:
            cost_anomalies.append(f"{date_str} cost 偏高（${cost:.2f} / {total:,} Token）")

    anomaly_text = cost_anomalies[0] if cost_anomalies else "无明显异常"
    observations = build_observations(agent_summary, peak_date, peak_date_total, cost_anomalies)
    judgement = build_judgement(agent_summary, peak_date, cost_anomalies)
    chart_lines = build_bar_chart(date_totals, end, days=7)

    lines = []
    lines.append(f"📊 Token 用量分析（{label}）")
    lines.append("")
    lines.append("【结论】")
    lines.append(f"- 总 Token：{grand_total:,}")
    lines.append(f"- 总 Cost：${grand_cost:.2f}" if any_cost_known else "- 总 Cost：不可用")
    lines.append(f"- 主消耗 Agent：{top_agent_text}")
    lines.append(f"- 峰值日期：{peak_date}" if peak_date else "- 峰值日期：无")
    lines.append(f"- 异常提示：{anomaly_text}")
    lines.append("")
    lines.append("【Agent 明细】")
    for idx, item in enumerate(agent_summary, start=1):
        lines.append(f"{idx}. {item['agent']}")
        lines.append(f"   - Token：{item['token']:,}")
        lines.append(f"   - Cost：${item['cost']:.2f}" if item['cost_known'] else "   - Cost：不可用")
        lines.append(f"   - Sessions：{item['sessions']}")
        lines.append(f"   - 占比：{item['share']:.1f}%")
        lines.append("")
    lines.append("【7 天趋势图】")
    lines.extend(chart_lines)
    lines.append("")
    lines.append("【关键观察】")
    for obs in observations:
        lines.append(f"- {obs}")
    lines.append("")
    lines.append("【一句话判断】")
    lines.append(judgement)
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
