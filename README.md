# 🦞 Token Usage Analysis

OpenClaw Token 用量分析工具 - 自动收集 + 智能分析

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-blue)](https://openclaw.ai)

---

## 📖 简介

自动收集和统计 OpenClaw 各 Agent 的 Token 用量，支持按 Agent、日期、时间范围多维度分析。帮助你了解 Token 消耗情况，优化使用成本。

### ✨ 主要功能

- 🕐 **自动收集** - 每小时自动记录各 Agent 的 Token 用量快照
- 📊 **多维度分析** - 按 Agent、日期、Session 分组统计
- 🔍 **灵活查询** - 支持 24 小时/7 天/30 天/周末/自定义范围查询
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

# 2. 检查 macOS launchd 任务（macOS 用户）
launchctl list | grep "com.token-usage"
# 输出示例：-    78    com.token-usage.collector

# 3. 手动触发一次收集
~/.openclaw/bin/collect-usage
# 输出示例：✅ 已收集 4 个 session 快照 (2026-03-10T14:00:00)

# 4. 查看日志文件
ls -lh ~/.openclaw/logs/session-usage.log
# 输出示例：-rw-r--r--  1 fx  staff  105K Mar 10 14:00 session-usage.log
```

**💡 提示**：安装后建议等待 24 小时再查询，获得完整的用量报告。

---

## 📊 使用方法

### 通过对话查询（推荐）

安装后，直接对 OpenClaw 说以下命令：

| 命令 | 说明 |
|------|------|
| `查 Token 用量` | 选择时间范围后输出报告 |
| `查上周末的 Token 用量` | 直接输出上周末报告 |
| `查过去 7 天的用量` | 直接输出 7 天报告 |
| `Token 用量分析` | 同上 |

### 时间范围选项

查询时会提供以下选项：

1. **过去 24 小时** - 快速查看最近用量
2. **过去 7 天** - 周维度汇总
3. **过去 30 天** - 月维度汇总
4. **上周末** - 最近一个周六 + 周日
5. **上周** - 上周一到周日
6. **自定义日期范围** - 手动输入起止日期

### 输出示例

**过去 7 天报告（真实数据）：**

```
======================================================================
🦞 Token 用量汇总分析（过去 7 天）
======================================================================

📊 Agent: main
------------------------------------------------------------
  📅 2026-03-07 (周六):
     Token: 2,313,060 (in=2,233,648, out=79,412)
     Sessions: 20
  📅 2026-03-08 (周日):
     Token: 7,093,884 (in=6,987,052, out=106,832)
     Sessions: 32
  📅 2026-03-09 (周一):
     Token: 6,174,705 (in=6,140,854, out=33,851)
     Sessions: 31

  📈 合计:
     Token: 15,581,649 (in=15,361,554, out=220,095)
     Sessions: 93

📊 Agent: tg-office
------------------------------------------------------------
  📅 2026-03-07 (周六):
     Token: 352,734 (in=332,800, out=19,934)
     Sessions: 3

  📈 合计:
     Token: 366,253 (in=345,698, out=20,555)
     Sessions: 7

======================================================================
📊 总计（所有 Agent）
------------------------------------------------------------
总 Token: 15,947,902 (in=15,707,252, out=240,650)
总 Sessions: 100

💡 用量分布:
- main: 97.7%
- tg-office: 2.3%
======================================================================
```

### 命令行查询

```bash
# 诊断状态
~/.openclaw/bin/collect-usage --diagnose

# 手动触发收集
~/.openclaw/bin/collect-usage

# 清理旧日志
~/.openclaw/bin/collect-usage --cleanup
```

---

## 📁 文件结构

```
token-usage-analysis/
├── SKILL.md                          # 技能说明
├── README.md                         # 本文件
├── SECURITY_AUDIT.md                 # 安全审计报告
├── PUBLISH.md                        # 发布指南
├── clawhub.yaml                      # ClawHub 配置
├── install.sh                        # 安装脚本
├── uninstall.sh                      # 卸载脚本
├── src/
│   ├── collector.py                  # 日志收集器（增量统计）
│   └── analyzer.py                   # 分析脚本
├── services/
│   └── com.token-usage.collector.plist  # macOS 定时任务配置
└── logs/  (运行时生成)
    ├── session-usage.log             # 用量日志
    └── collector-state.json          # 增量统计状态文件
```

---

## 🔧 配置说明

### 定时任务频率

默认每小时执行一次（整点），如需修改：

**macOS (launchd)**:
编辑 `services/com.token-usage.collector.plist`，修改 `StartCalendarInterval` 配置。

**Linux (cron)**:
编辑 crontab，修改执行频率。

### 日志管理

- **日志位置**: `~/.openclaw/logs/session-usage.log`
- **大小限制**: 10MB（超出自动轮转压缩）
- **保留期限**: 90 天（自动清理旧日志）
- **收集频率**: 每小时 1 次
- **状态文件**: `~/.openclaw/logs/collector-state.json`（记录增量进度）

### 📈 性能数据

| 指标 | 数值 |
|------|------|
| 单次收集耗时 | ~1-3 秒 |
| 日志日增长量 | ~50-150 KB/天 |
| 内存占用 | <50MB |
| CPU 占用 | 瞬时 <5% |

**实际测试环境**: macOS 14.x, OpenClaw 0.9.x, 2 个活跃 Agent

---

## 🔒 安全说明

本技能已通过安全审计，确认：

- ✅ 不读取任何 API Key 或认证信息
- ✅ 不访问网络
- ✅ 不外发任何数据
- ✅ 仅读取本地 session 文件中的 usage 字段
- ✅ 日志文件仅包含用量统计，不含对话内容

详细审计报告：[SECURITY_AUDIT.md](SECURITY_AUDIT.md)

### 数据访问范围

**读取**:
- `~/.openclaw/agents/*/sessions/*.jsonl` - 仅读取 usage 字段（Token 统计）

**写入**:
- `~/.openclaw/logs/session-usage.log` - 用量日志
- `~/.openclaw/logs/token-usage-collector.log` - 收集器运行日志

---

## ❓ 常见问题

### Q: 为什么查询时显示"没有数据"？

**A**: 可能原因：
1. 刚安装技能，数据还在积累中（建议 24 小时后查询）
2. 定时任务未正常运行（运行 `collect-usage --diagnose` 检查）

### Q: 如何修改收集频率？

**A**: 编辑 `services/com.token-usage.collector.plist`，修改 `StartCalendarInterval` 配置。

### Q: 日志文件太大怎么办？

**A**: 自动轮转已启用，也可手动运行 `collect-usage --cleanup` 清理旧日志。

### Q: 如何卸载？

**A**: 运行以下命令：
```bash
~/.openclaw/workspace/skills/token-usage-analysis/uninstall.sh
```

---

## 📝 更新日志

### v1.1.0 (2026-03-13) - 🆕 当前版本

- 🔧 **修复**: collector.py 改为增量统计，避免重复累加历史数据
- 🔧 **新增**: 状态文件 `collector-state.json` 记录每个 session 的累计进度
- 🔧 **修复**: analyzer.py 移除 cost 显示（因模型配置中 cost 均为 0）
- ✅ **数据准确性**: 与 OpenClaw Dashboard 保持一致

### v1.0.1 (2026-03-10)

- 📝 更新 README，添加真实输出示例
- 📊 添加性能数据表格
- ✅ 完善安装验证步骤
- 🔧 优化安装脚本，增加详细输出

### v1.0.0 (2026-03-09)

- 🎉 初始版本发布
- ✅ 支持每小时自动收集 Token 用量
- ✅ 支持多维度用量分析（按 Agent/日期/时间范围）
- ✅ 支持日志自动轮转（10MB 限制）和清理（90 天保留）
- ✅ 跨平台支持（macOS launchd / Linux cron）
- ✅ 通过安全审计，无敏感信息泄露
- 📊 支持 6 种时间范围查询（24h/7d/30d/周末/上周/自定义）
- 💡 多 Agent 用量分布百分比显示

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 🙏 致谢

- [OpenClaw](https://openclaw.ai) - 强大的 AI 助手框架
- [ClawHub](https://clawhub.com) - OpenClaw 技能市场

---

## 📞 支持

遇到问题？

1. 运行诊断：`collect-usage --diagnose`
2. 查看日志：`~/.openclaw/logs/token-usage-collector.log`
3. 提交 Issue：[GitHub Issues](https://github.com/jackwude/token-usage-analysis/issues)

---

<div align="center">

**Made with ❤️ by 麻辣小龙虾 🦞**

[⭐ Star this repo](https://github.com/jackwude/token-usage-analysis) if you find it useful!

</div>
