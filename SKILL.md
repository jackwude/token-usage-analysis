# Token Usage Analysis Skill

自动收集和统计 OpenClaw / Agent 会话 Token 用量，支持按 Agent/日期/时间范围分析。

## 功能特性

- ✅ **自动收集**：每小时自动记录各 Agent 的 Token 用量
- ✅ **多维度分析**：按 Agent、日期、Session 分组统计
- ✅ **灵活查询**：支持 24 小时/7 天/30 天/周末/自定义范围
- ✅ **日志轮转**：自动管理日志大小（10MB 限制 + 90 天保留）
- ✅ **跨平台**：支持 macOS (launchd) 和 Linux (cron)

## 安装

```bash
# 1. 进入技能目录
cd ~/.openclaw/workspace/skills/token-usage-analysis

# 2. 运行安装脚本
./install.sh
```

安装后会自动：
- 创建日志目录 (`~/.openclaw/logs/`)
- 配置定时任务（每小时执行）
- 执行首次日志收集

## 使用

### 通过对话查询

直接对我说以下命令：

- "查 Token 用量" → 选择时间范围后输出报告
- "查上周末的 Token 用量" → 直接输出上周末报告
- "查过去 7 天的用量" → 直接输出 7 天报告
- "Token 用量分析" → 同上

### 触发边界

本 Skill 负责 **OpenClaw / Agent / 会话级别** 的 Token 用量分析。

优先由本 Skill 处理的说法包括：
- "查 Token 用量"
- "Token 用量"
- "Token 消耗"
- "查过去24小时的 Token 用量"
- "会话 Token 用量"
- "Agent Token 用量"

以下说法**不属于本 Skill**，应交给 `bailian-usage`：
- "百炼 Token"
- "百炼用量"
- "百炼额度"
- "阿里云百炼"
- "Coding Plan"
- "百炼套餐用量"

### 时间范围选项

查询时会提供以下选项：
1. 过去 24 小时
2. 过去 7 天
3. 过去 30 天
4. 上周末（最近一个周六 + 周日）
5. 上周（周一到周日）
6. 自定义日期范围

### 命令行查询

```bash
# 诊断状态
~/.openclaw/bin/collect-usage --diagnose

# 手动触发收集
~/.openclaw/bin/collect-usage

# 清理旧日志
~/.openclaw/bin/collect-usage --cleanup
```

## 输出示例

```
======================================================================
🦞 Token 用量汇总分析（上周末 (03/07 周六 ~ 03/08 周日)）
======================================================================

📊 Agent: main
------------------------------------------------------------
  📅 2026-03-07 (周六):
     Token: 2,313,060 (in=2,233,648, out=79,412)
     Cost:  $7.73
     Sessions: 20

  📈 合计:
     Token: 9,406,944
     Cost:  $30.96
     Sessions: 52

======================================================================
📊 总计（所有 Agent）
------------------------------------------------------------
总 Token: 9,773,197
总 Cost: $32.27
总 Sessions: 57
======================================================================
```

## 卸载

```bash
cd ~/.openclaw/workspace/skills/token-usage-analysis
./uninstall.sh
```

## 文件结构

```
token-usage-analysis/
├── SKILL.md                  # 本文件
├── install.sh                # 安装脚本
├── uninstall.sh              # 卸载脚本
├── src/
│   ├── collector.py          # 日志收集器
│   └── analyzer.py           # 分析报告生成
├── bin/
│   ├── collect-usage         # 收集入口（安装后生成）
│   └── analyze-usage         # 分析入口（安装后生成）
└── services/
    └── com.token-usage.collector.plist  # macOS 定时任务配置
```

## 日志管理

- **日志位置**: `~/.openclaw/logs/session-usage.log`
- **大小限制**: 10MB（超出自动轮转压缩）
- **保留期限**: 90 天（自动清理旧日志）
- **收集频率**: 每小时 1 次

## 常见问题

### Q: 为什么查询时显示"没有数据"？
A: 可能原因：
1. 刚安装技能，数据还在积累中（建议 24 小时后查询）
2. 定时任务未正常运行（运行 `collect-usage --diagnose` 检查）

### Q: 如何修改收集频率？
A: 编辑 `services/com.token-usage.collector.plist`，修改 `StartCalendarInterval` 配置

### Q: 日志文件太大怎么办？
A: 自动轮转已启用，也可手动运行 `collect-usage --cleanup` 清理旧日志

## 版本

- **当前版本**: 1.1.0
- **作者**: 麻辣小龙虾 🦞
- **许可证**: MIT

## 更新日志

### v1.1.0 (2026-03-13)
- 🔧 **修复**: collector.py 改为增量统计，避免重复累加历史数据
- 🔧 **新增**: 状态文件 `collector-state.json` 记录每个 session 的累计进度
- 🔧 **修复**: analyzer.py 移除 cost 显示（因模型配置中 cost 均为 0）
- ✅ **数据准确性**: 与 OpenClaw Dashboard 保持一致

### v1.0.0 (2026-03-09)
- 初始版本发布
- 支持每小时自动收集
- 支持多维度用量分析
- 支持日志自动轮转和清理
