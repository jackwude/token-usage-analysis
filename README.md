# 🦞 Token Usage Analysis

OpenClaw Token 用量分析工具 - 自动收集 + 对话式分析

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-blue)](https://openclaw.ai)

---

## 📖 简介

自动收集和统计 OpenClaw 各 Agent 的 Token 用量，支持按时间范围、Agent、占比、峰值和异常做分析。

这个 Skill 现在默认面向 **对话查询**，不是只给命令行用的脚本包。

### ✨ 主要功能

- 🕐 **自动收集** - 每小时自动记录各 Agent 的 Token 用量快照
- 💬 **对话式查询** - 直接问“查过去 7 天 Token”即可输出报告
- 📊 **固定结果模板** - 统一输出结论、明细、趋势图、观察、判断
- 📈 **7 天文本柱状图** - 直接展示每日变化趋势
- 🔍 **异常提示** - 自动标记疑似成本异常日期
- 🗂️ **日志轮转** - 自动管理日志大小（10MB 限制 + 90 天保留）
- 💻 **跨平台** - 支持 macOS (launchd) 和 Linux (cron)

---

## 🚀 快速开始

### 前置要求

- Python 3.7+
- macOS 或 Linux
- OpenClaw 0.9.0+

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/jackwude/token-usage-analysis.git ~/.openclaw/workspace/skills/token-usage-analysis

# 2. 运行安装脚本
~/.openclaw/workspace/skills/token-usage-analysis/install.sh
```

安装后会自动：
- ✅ 创建日志目录 (`~/.openclaw/logs/`)
- ✅ 配置定时任务（每小时执行）
- ✅ 执行首次日志收集

### 验证安装

```bash
# 1. 检查定时任务状态
~/.openclaw/bin/collect-usage --diagnose

# 2. 手动触发一次收集
~/.openclaw/bin/collect-usage

# 3. 查看日志文件
ls -lh ~/.openclaw/logs/session-usage.log
```

**💡 提示**：安装后建议等待一段时间再查询，数据越完整，分析越有价值。

---

## 💬 使用方法

### 通过对话查询（推荐）

安装后，直接对 OpenClaw 说：

- `查 Token`
- `查 Token 用量`
- `Token 用量分析`
- `查过去 7 天 Token`
- `查最近 24 小时 Token`
- `查上周 Token`
- `查上周末 Token`
- `查 main 的 Token 用量`
- `哪个 Agent 用量最高`
- `最近哪天 Token 花得最多`

### 时间范围

默认支持：

1. 过去 24 小时
2. 过去 7 天
3. 过去 30 天
4. 上周末
5. 上周
6. 自定义日期范围

### 输出模板（已固化）

所有报告默认按以下结构输出：

1. `【结论】`
2. `【Agent 明细】`
3. `【7 天趋势图】`
4. `【关键观察】`
5. `【一句话判断】`

---

## 📊 输出示例

**过去 7 天报告（新模板）：**

```markdown
📊 Token 用量分析（过去 7 天）

【结论】
- 总 Token：16,106,551
- 总 Cost：$44.98
- 主消耗 Agent：main（97.4%）
- 峰值日期：2026-03-08
- 异常提示：2026-03-11 cost 偏高（$12.42 / 121,310 Token）

【Agent 明细】
1. main
   - Token：15,691,179
   - Cost：$43.55
   - Sessions：113
   - 占比：97.4%

2. tg-office
   - Token：415,372
   - Cost：$1.44
   - Sessions：8
   - 占比：2.6%

【7 天趋势图】
03-05 | ▏ 0.00M
03-06 | ▏ 0.00M
03-07 | ████████████ 2.67M
03-08 | ████████████████████████████████ 7.11M
03-09 | ████████████████████████████ 6.17M
03-10 | █ 0.04M
03-11 | █ 0.12M

【关键观察】
- 用量高度集中在 main（97.4%）
- 峰值日期是 2026-03-08，单日消耗 7,107,403 Token
- 发现成本异常：2026-03-11 cost 偏高（$12.42 / 121,310 Token）

【一句话判断】
该时间段属于 main 主导的消耗模式，且存在成本异常，建议优先排查 cost 口径。
```

---

## 🧠 分析逻辑

### 当前支持

- 按时间范围汇总 Token 用量
- 按 Agent 输出占比与明细
- 识别峰值日期
- 生成最近 7 个自然日的文本柱状图
- 检测疑似成本异常

### 当前局限

- 统计基于快照差分，不是逐事件精确记账
- 若 session 中途重置、截断、跨天或日志缺失，结果可能有误差
- 当前更擅长时间范围汇总，后续可继续增强 Agent 过滤、排名、模型维度分析

---

## 🧰 命令行（安装 / 诊断 / 排障）

```bash
# 诊断状态
~/.openclaw/bin/collect-usage --diagnose

# 手动触发收集
~/.openclaw/bin/collect-usage

# 清理旧日志
~/.openclaw/bin/collect-usage --cleanup

# 直接运行分析脚本（示例）
python3 ~/.openclaw/workspace/skills/token-usage-analysis/src/analyzer.py 7d
```

---

## 📁 文件结构

```text
token-usage-analysis/
├── SKILL.md
├── README.md
├── SECURITY_AUDIT.md
├── PUBLISH.md
├── clawhub.yaml
├── install.sh
├── uninstall.sh
├── references/
│   └── output-template.md
├── src/
│   ├── collector.py
│   └── analyzer.py
└── services/
    └── com.token-usage.collector.plist
```

---

## 🔧 配置说明

### 日志管理

- **日志位置**: `~/.openclaw/logs/session-usage.log`
- **大小限制**: 10MB（超出自动轮转压缩）
- **保留期限**: 90 天（自动清理旧日志）
- **收集频率**: 每小时 1 次

### 定时任务频率

默认每小时执行一次（整点）。

- **macOS (launchd)**：编辑 `services/com.token-usage.collector.plist`
- **Linux (cron)**：编辑 crontab

---

## 🔒 安全说明

本技能已通过安全审计，确认：

- ✅ 不读取任何 API Key 或认证信息
- ✅ 不访问网络
- ✅ 不外发任何数据
- ✅ 仅读取本地 session 文件中的 usage 字段
- ✅ 日志文件仅包含用量统计，不含对话内容

### Cost 字段口径说明

- 报告中的 `Cost` 来自 session 行内 `usage.cost.total`（若该字段存在）
- 若你的环境不提供成本字段，`Cost` 可能为 `0` 或显示为 `NA`

详细审计报告见：`SECURITY_AUDIT.md`

---

## ❓ 常见问题

### Q: 为什么查询时显示“没有数据”？

可能原因：
1. 刚安装，数据还在积累中
2. 定时任务未正常运行
3. 所选时间范围内 session 没有有效变化

### Q: 为什么有些日期是 0？

因为趋势图默认展示**最近 7 个自然日**。如果某天没有有效增量，会显示为 0。

### Q: 为什么 Token 不高但 Cost 看起来很高？

这通常说明：
- 成本统计口径发生变化
- 底层 `usage.cost.total` 存在异常
- 该日期发生了不成比例的费用增长

### Q: 如何卸载？

```bash
~/.openclaw/workspace/skills/token-usage-analysis/uninstall.sh
```

---

## 📝 更新日志

### v1.1.0 (2026-03-11)

- ✅ 将 Skill 重构为**对话优先**模式
- ✅ 固化结果输出模板
- ✅ 新增 `【7 天趋势图】` 文本柱状图
- ✅ 新增异常提示与一句话判断
- ✅ README 同步到最新逻辑

### v1.0.0 (2026-03-09)

- 🎉 初始版本发布
- ✅ 支持每小时自动收集 Token 用量
- ✅ 支持多维度用量分析（按 Agent/日期/时间范围）
- ✅ 支持日志自动轮转（10MB 限制）和清理（90 天保留）
- ✅ 跨平台支持（macOS launchd / Linux cron）

---

## 📞 支持

遇到问题时建议按顺序排查：

1. 运行诊断：`collect-usage --diagnose`
2. 查看日志：`~/.openclaw/logs/token-usage-collector.log`
3. 检查定时任务是否正常运行
4. 检查 `session-usage.log` 是否持续增长

---

**Made with ❤️ by 麻辣小龙虾 🦞**
