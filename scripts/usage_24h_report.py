import os, re, sys
from datetime import datetime, timedelta
from collections import defaultdict

LOCAL_TZ = datetime.now().astimezone().tzinfo

log_path = os.path.expanduser('~/.openclaw/logs/session-usage.log')
if not os.path.exists(log_path):
    print('日志不存在：', log_path)
    sys.exit(0)

rx = re.compile(r'^(?P<ts>[^ ]+) \| agent=(?P<agent>[^ ]+) \| session=(?P<session>[^ ]+) \| model=(?P<model>[^ ]+) \| tokens_in=(?P<tin>\d+) \| tokens_out=(?P<tout>\d+) \| cost=\$(?P<cost>[0-9.]+) ')

def parse_iso(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TZ)
    return dt

now = datetime.now().astimezone()
cutoff = now - timedelta(hours=24)

rows = defaultdict(list)
with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        line = line.strip()
        m = rx.match(line)
        if not m:
            continue
        ts = parse_iso(m['ts'])
        if ts < cutoff:
            continue
        agent = m['agent']
        session = m['session']
        tin = int(m['tin']); tout = int(m['tout']); cost = float(m['cost'])
        rows[(agent, session)].append((ts, tin, tout, cost))

agent_sum = defaultdict(lambda: [0, 0, 0.0, 0])
for (agent, session), lst in rows.items():
    lst.sort(key=lambda x: x[0])
    first = lst[0]; last = lst[-1]
    dtin = last[1] - first[1]
    dtout = last[2] - first[2]
    dcost = last[3] - first[3]
    if dtin < 0: dtin = 0
    if dtout < 0: dtout = 0
    if dcost < 0: dcost = 0.0
    agent_sum[agent][0] += dtin
    agent_sum[agent][1] += dtout
    agent_sum[agent][2] += dcost
    agent_sum[agent][3] += 1

items = sorted(agent_sum.items(), key=lambda kv: (kv[1][0] + kv[1][1], kv[0]), reverse=True)
print(f"统计窗口：最近24小时（从 {cutoff.strftime('%Y-%m-%d %H:%M %Z')} 到 {now.strftime('%Y-%m-%d %H:%M %Z')}）")
if not items:
    print('（窗口内没有可用快照数据；可能是刚启用、或过去24小时没有运行/写入）')
    sys.exit(0)

for agent, (tin, tout, cost, scount) in items:
    total = tin + tout
    print(f"- {agent}: total={total:,} (in={tin:,}, out={tout:,}) | cost=${cost:.4f} | sessions={scount}")
