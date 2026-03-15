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
    """解析 ISO 时间戳，支持带/不带时区、带/不带微秒的格式"""
    # 先移除时区部分（如 +08:00 或 -05:00）
    if '+' in ts:
        ts_clean = ts.split('+')[0]
    elif ts.count('-') > 2:  # 有负时区偏移，如 2026-03-15T12:00:00-05:00
        # 找到最后一个 -（时区分隔符）
        idx = ts.rfind('-')
        ts_clean = ts[:idx]
    else:
        ts_clean = ts
    
    # 移除微秒部分（如果有）
    if '.' in ts_clean:
        ts_clean = ts_clean.split('.')[0]
    
    dt = datetime.fromisoformat(ts_clean)
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
    session_hourly = defaultdict(list)  # 新增：小时维度数据
    model_sessions = defaultdict(set)  # model -> set of sessions

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
            model = m['model']
            tin = int(m['tin'])
            tout = int(m['tout'])
            cost = float(m['cost'])
            date_str = ts.strftime('%Y-%m-%d')
            hour_str = ts.strftime('%m/%d %H:00')  # 新增：小时维度 key
            session_daily[(agent, session, date_str)].append((ts, tin, tout, cost, model))
            session_hourly[(agent, session, hour_str)].append((ts, tin, tout, cost, model))  # 新增
            model_sessions[model].add(session)

    agent_daily = defaultdict(lambda: defaultdict(lambda: {
        'total_in': 0,
        'total_out': 0,
        'cost': 0.0,
        'sessions': set(),
    }))

    model_totals = defaultdict(lambda: {'tokens_in': 0, 'tokens_out': 0, 'cost': 0.0, 'sessions': set()})

    raw_cost_daily = defaultdict(float)
    raw_cost_agent = defaultdict(float)
    raw_cost_model = defaultdict(float)
    raw_cost_total = 0.0

    for snapshots in session_daily.values():
        for _, _, _, cost, model in snapshots:
            raw_cost_total += cost
            raw_cost_model[model] += cost

    for (agent, _session, date_str), snapshots in session_daily.items():
        # 日志中存的是每次的增量，直接累加所有快照的增量即可
        total_in = sum(item[1] for item in snapshots)
        total_out = sum(item[2] for item in snapshots)
        total_cost = sum(item[3] for item in snapshots)
        
        day_snapshot_cost = total_cost
        raw_cost_daily[date_str] += day_snapshot_cost
        raw_cost_agent[agent] += day_snapshot_cost

        agent_daily[agent][date_str]['total_in'] += total_in
        agent_daily[agent][date_str]['total_out'] += total_out
        agent_daily[agent][date_str]['cost'] += total_cost
        agent_daily[agent][date_str]['sessions'].add(_session)

        # 累加模型统计（从最后一次快照获取 model）
        last = snapshots[-1]
        if last:
            model = last[4] if len(last) > 4 else "unknown"
            model_totals[model]['tokens_in'] += total_in
            model_totals[model]['tokens_out'] += total_out
            model_totals[model]['cost'] += total_cost
            model_totals[model]['sessions'].add(_session)

    if not agent_daily and raw_cost_total <= 0:
        return None, "⚠️ 该时间段内没有检测到有效的用量数据"

    return {
        'agent_daily': agent_daily,
        'session_hourly': session_hourly,  # 新增：返回小时维度数据
        'raw_cost_daily': raw_cost_daily,
        'raw_cost_agent': raw_cost_agent,
        'raw_cost_model': raw_cost_model,
        'raw_cost_total': raw_cost_total,
        'model_totals': dict(model_totals),
        'model_sessions': {k: len(v) for k, v in model_sessions.items()},
    }, None


def fmt_million(n: int) -> str:
    return f"{n / 1_000_000:.2f}M"


def fmt_thousands(n: int) -> str:
    """格式化为 K 单位"""
    return f"{n / 1_000:.1f}K"


def build_trend_lines(daily_totals: dict, hourly_totals: dict = None, is_24h: bool = False) -> list:
    if is_24h and hourly_totals is not None:
        # 24 小时窗口：按小时显示趋势（只显示有数据的小时，节省空间）
        if not hourly_totals:
            return ["- 无数据"]
        
        max_total = max(hourly_totals.values()) if hourly_totals else 0
        lines = []
        
        # 生成 24 个小时的标签（从当前时间往前推 24 小时）
        now = datetime.now()
        displayed_count = 0
        max_display = 12  # 最多显示 12 个小时，避免太长
        
        for i in range(23, -1, -1):
            hour_dt = now - timedelta(hours=i)
            hour_key = hour_dt.strftime('%m/%d %H:00')
            total = hourly_totals.get(hour_key, 0)
            
            # 只显示有数据的小时，节省空间
            if total > 0 and displayed_count < max_display:
                label = hour_dt.strftime('%H:00')
                if max_total <= 0:
                    bar = "█"
                    bar_display = fmt_thousands(total)
                else:
                    bar_len = max(1, round(total / max_total * 20))
                    bar = "█" * bar_len
                    bar_display = fmt_thousands(total)
                lines.append(f"{label} | {bar} {bar_display}")
                displayed_count += 1
        
        if not lines:
            return ["- 无数据"]
        return lines
    else:
        # 多日窗口：按天显示趋势
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
    session_hourly = data.get('session_hourly', {})  # 新增：获取小时维度数据

    agent_totals = {}
    agent_sessions = {}
    daily_totals = defaultdict(int)
    hourly_totals = defaultdict(int)  # 新增：小时总量

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

    # 计算小时总量（用于 24 小时趋势图）
    for (agent, session, hour_str), snapshots in session_hourly.items():
        # 日志中存的是增量，直接累加
        for item in snapshots:
            hourly_totals[hour_str] += item[1] + item[2]

    # 判断是否是 24 小时窗口
    is_24h = (end - start).total_seconds() <= 24 * 3600

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

    # 模型维度统计
    lines.append("【模型分布】")
    model_totals = data.get('model_totals', {})
    model_sessions = data.get('model_sessions', {})
    
    if model_totals:
        sorted_models = sorted(model_totals.items(), key=lambda x: x[1]['tokens_in'] + x[1]['tokens_out'], reverse=True)
        for idx, (model, stats) in enumerate(sorted_models, start=1):
            total_tokens = stats['tokens_in'] + stats['tokens_out']
            pct = (total_tokens / grand_total * 100) if grand_total > 0 else 0.0
            cost = stats['cost']
            sessions_count = len(stats['sessions'])
            lines.append(f"{idx}. {model}")
            lines.append(f"   - Token：{total_tokens:,} (in={stats['tokens_in']:,}, out={stats['tokens_out']:,})")
            lines.append(f"   - Sessions：{sessions_count}")
            lines.append(f"   - 占比：{pct:.1f}%")
            lines.append(f"   - 成本：${cost:.4f}")
            lines.append("")
    else:
        lines.append("1. 无模型数据")
        lines.append("")

    lines.append("【趋势图】")
    lines.extend(build_trend_lines(daily_totals, hourly_totals, is_24h))
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
