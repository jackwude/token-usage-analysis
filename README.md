# token-usage-analysis

一个给 OpenClaw 用的本地统计技能：定时收集 session 的 usage 数据，按时间范围汇总 Token 用量，方便看成本和排查异常。

- 仓库：`https://github.com/jackwude/token-usage-analysis.git`
- 适用系统：macOS / Linux
- Python：3.7+
- OpenClaw：0.9.0+

## 它做什么

这个技能主要做两件事：

1. 每小时收集一次各 Agent/session 的用量快照
2. 按 24h / 7d / 30d / 上周 / 上周末 / 自定义区间做汇总分析

另外还带了日志轮转和旧日志清理，适合长期跑。

## 快速安装

```bash
git clone https://github.com/jackwude/token-usage-analysis.git ~/.openclaw/workspace/skills/token-usage-analysis
~/.openclaw/workspace/skills/token-usage-analysis/install.sh
```

安装脚本会自动：

- 创建日志目录 `~/.openclaw/logs/`
- 配置定时任务（默认每小时）
- 触发一次首次收集

## 安装后先做这 4 步

```bash
# 1) 看诊断
~/.openclaw/bin/collect-usage --diagnose

# 2) 手动跑一次
~/.openclaw/bin/collect-usage

# 3) 看日志是否生成
ls -lh ~/.openclaw/logs/session-usage.log

# 4) macOS 可选：确认 launchd 任务
launchctl list | grep "com.token-usage"
```

如果刚装完就查不到数据，通常是正常现象。等几个收集周期后再看会更完整。

## 对话里怎么触发

安装完成后，直接对 OpenClaw 说下面这类话就行：

- `查 Token 用量`
- `查过去 7 天的 Token 用量`
- `查上周末的 Token 用量`
- `Token 用量分析`

## 命令行用法

```bash
# 诊断
~/.openclaw/bin/collect-usage --diagnose

# 手动收集
~/.openclaw/bin/collect-usage

# 清理旧日志
~/.openclaw/bin/collect-usage --cleanup
```

## 项目结构

```text
token-usage-analysis/
├── SKILL.md
├── README.md
├── SECURITY_AUDIT.md
├── PUBLISH.md
├── clawhub.yaml
├── install.sh
├── uninstall.sh
├── src/
│   ├── collector.py
│   └── analyzer.py
└── services/
    └── com.token-usage.collector.plist
```

## 配置说明

### 定时频率

默认每小时一次。

- macOS：改 `services/com.token-usage.collector.plist`
- Linux：改 cron 表达式

### 日志策略

- `~/.openclaw/logs/session-usage.log`
- 超过 10MB 自动轮转
- 默认保留 90 天
- 状态文件：`~/.openclaw/logs/collector-state.json`

## 安全边界

这个技能不访问外网，不读取密钥，不上传数据。

读取范围（只读 usage 统计）：

- `~/.openclaw/agents/*/sessions/*.jsonl`

写入范围：

- `~/.openclaw/logs/session-usage.log`
- `~/.openclaw/logs/token-usage-collector.log`
- `~/.openclaw/logs/collector-state.json`

详细内容见 `SECURITY_AUDIT.md`。

## 常见问题

### 1) 查询结果是“没有数据”

常见原因：

- 刚安装，采样还不够
- 定时任务没跑起来

先执行：

```bash
~/.openclaw/bin/collect-usage --diagnose
```

### 2) 想改收集频率

- macOS：编辑 plist
- Linux：编辑 cron

改完建议手动执行一次 `collect-usage` 验证。

### 3) 如何卸载

```bash
~/.openclaw/workspace/skills/token-usage-analysis/uninstall.sh
```

## 更新日志

### v1.2.0 (2026-03-13)

- 支持多模型 Token 估算（OpenAI / Anthropic / Bailian）
- 有真实数据优先真实数据，缺失时自动估算
- 修复 cost 字段提取（`usage.cost.total`）

### v1.1.0 (2026-03-13)

- collector 改为增量统计，避免重复累加
- 新增 `collector-state.json` 记录 session 进度

### v1.0.0 (2026-03-09)

- 初始版本发布
- 支持自动收集、区间分析、日志轮转、跨平台任务调度

## 贡献

欢迎提 issue 或 PR：

1. Fork
2. 新建分支
3. 提交修改
4. Push
5. 发起 PR

## License

MIT
