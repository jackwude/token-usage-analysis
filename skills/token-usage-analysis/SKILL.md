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
📊 Token 用量分析（过去 7 天）

【结论】
- 总 Token：4,081
- 主消耗 Agent：main（100.0%）
- 峰值日期：2026-03-14
- 异常提示：无明显异常

【Agent 明细】
1. main
   - Token：4,081
   - Sessions：24
   - 占比：100.0%

【模型分布】
1. qwen3.5-plus
   - Token：4,081 (in=1,356, out=2,725)
   - Sessions：24
   - 占比：100.0%
   - 成本：$0.0382

【趋势图】
03-13 | █ 0.00M
03-14 | ████████████████████████████████ 0.00M

【关键观察】
- 用量主要集中在 main（100.0%）
- 峰值出现在 2026-03-14（0.00M）

【一句话判断】
过去 7 天 的用量主要集中在 main，整体分布清晰，暂无明显异常。
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

- **当前版本**: 1.2.0
- **作者**: 麻辣小龙虾 🦞
- **许可证**: MIT

## 更新日志

### v1.2.0 (2026-03-14)
- ✨ **新增**: 报告新增【模型分布】模块，显示各模型的 Token 用量、Sessions、占比和成本
- 🔧 **修复**: collector.py 添加 tiktoken 估算逻辑，支持 Bailian 等无官方用量 API 的模型
- 🔧 **修复**: global-session-usage-logger.sh 支持新版 usage 嵌套格式
- ✅ **数据完整性**: Bailian 模型现在可通过 tiktoken 估算 Token 用量

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
