# Agent 创建器 - 完整方案文档

**版本**: v1.0  
**创建时间**: 2026-03-15  
**最后更新**: 2026-03-15  

---

## 📖 项目概述

创建一个 **Agent 创建器**（元 Agent），用于引导用户创建、管理和维护其他 Agent。它不是死板的表单工具，而是能理解需求、主动推荐配置的智能助手。

---

## 🎯 核心定位

| 维度 | 设计 |
|-----|------|
| **身份** | 独立 Agent，与 main、tg-office 并列 |
| **Agent 名称** | `agent-creator` |
| **显示名** | Agent 工厂 🏭 |
| **人格** | 专业、耐心、善于引导、像产品顾问 |
| **职责** | 引导用户创建新 Agent、收集需求、推荐配置、生成文件、自动启动、全生命周期管理 |
| **渠道** | Telegram（独立 Bot Token） |
| **Workspace** | `~/.openclaw/workspace-agent-creator/` |
| **模型** | bailian/qwen3.5-plus |

---

## 📋 功能清单

### 支持的操作（自然语言触发）

| 功能 | 触发示例 | 说明 |
|-----|---------|------|
| **创建 Agent** | "帮我创建一个日程助理" | 引导式 7 步流程 |
| **查看列表** | "看看我有哪些 Agent" | 列出所有 Agent + 状态 |
| **查看详情** | "创作助手的配置是什么样的" | 展示单个 Agent 配置 |
| **修改配置** | "把创作助手的模型改成 qwen-max" | 名称不可改，其他都可改 |
| **禁用** | "停用资讯监控员" | 改状态为 disabled，保留配置 |
| **启用** | "启用日程助理" | 恢复活跃状态 |
| **删除** | "删除创作助手" | 移到回收站，保留 7 天（需二次确认） |
| **健康检查** | "检查创作助手是否正常" | Session 状态 + 渠道连接 + 文件完整性 |

---

## 🏗️ 技术设计

### 1. 架构模式

```
OpenClaw Gateway (单进程)
│
├── Session: main
├── Session: tg-office
├── Session: agent-creator     ← 创建器本身
├── Session: content-creator   ← 被创建的 Agent 示例
└── Session: schedule-assistant
```

- **共享**：主 `openclaw.json` 配置、Gateway 进程、Skills 池、模型池
- **隔离**：各自 workspace、memory、对话历史、Bot Token

---

### 2. Bot Token 设计

**每个 Agent 独立 Bot Token，不共用**

**存储结构**（主 `openclaw.json`）：
```json
{
  "plugins": {
    "telegram": [
      {
        "id": "main-bot",
        "token": "123456:ABC...",
        "sessions": ["main"]
      },
      {
        "id": "creator-bot",
        "token": "789012:DEF...",
        "sessions": ["agent-creator"]
      },
      {
        "id": "content-bot",
        "token": "345678:GHI...",
        "sessions": ["content-creator"]
      }
    ]
  }
}
```

**优点**：
- 每个 Agent 独立身份，用户容易区分
- 某个 Bot 被封不影响其他 Agent
- 可以独立设置 Bot 名字、头像

---

### 3. 配置存储（方案 A：分层存储）

| 信息类型 | 存储位置 | 原因 |
|---------|---------|------|
| **Bot Token 等敏感凭证** | 主 `openclaw.json` 的 `plugins` 配置 | 渠道是 Gateway 级别的，多个 Agent 可共享同一个 Bot 配置结构 |
| **Agent 个性化配置** | 各 Agent 自己的 workspace | 每个 Agent 独立的人格、职责、偏好 |
| **渠道绑定关系** | 主配置或单独的 `agents/registry.json` | 记录哪个 Agent 绑定哪个渠道/Chat ID |

---

### 4. 删除策略

**回收站模式**：
- 删除时移到 `~/.openclaw/backup-agents/[agent-name]/`
- 保留 7 天，超期自动清理
- 支持恢复（7 天内）

---

### 5. 命令识别

**自然语言 + 关键词匹配**

| 关键词 | 意图 |
|-------|------|
| 创建/新建/搞一个 | 创建 Agent |
| 查看/列出/有哪些 | 查看列表 |
| 配置/设置/是什么样的 | 查看详情 |
| 修改/改成/调整 | 修改配置 |
| 停用/禁用/暂停 | 禁用 |
| 启用/激活/恢复 | 启用 |
| 删除/删掉/不要了 | 删除 |
| 检查/健康/是否正常 | 健康检查 |

---

### 6. 错误处理

**错误报告格式**：
```
❌ 创建失败：session 启动失败

**原因**：配置中的模型名称无效
**具体错误**：model "qwen3.5-plus" not found in available models
**已尝试**：
- ✅ workspace 文件已生成
- ✅ 主配置已更新
- ❌ session 启动失败

**建议**：
1. 检查模型名称是否正确（可用模型：qwen3-plus, qwen-max...）
2. 运行命令：openclaw models list 查看可用模型
3. 修复后重试，或联系管理员

**已回滚**：配置已恢复到创建前状态
```

**处理原则**：
- 原子操作：要么全成功，要么全回滚
- 具体原因 + 已尝试 + 建议
- 修改主配置前自动备份

---

### 7. 健康检查

**检查项**（不验证模型有效性）：
| 检查项 | 方法 |
|-------|------|
| **Session 状态** | 检查 session 是否活跃 |
| **渠道连接** | 发送测试消息 |
| **文件完整性** | 检查必需文件是否存在（SOUL.md、USER.md、config.json 等） |

---

## 📁 目录结构

```
~/.openclaw/
├── openclaw.json              # 主配置（含所有 Bot Token）
├── openclaw.json.bak          # 修改前自动备份
│
├── workspace-agent-creator/   # 创建器自己的 workspace
│   ├── SOUL.md
│   ├── USER.md
│   ├── MEMORY.md
│   └── config.json
│
├── workspace-content-creator/ # 内容创作助手 workspace
│   ├── SOUL.md
│   ├── USER.md
│   ├── MEMORY.md
│   └── config.json
│
├── workspace-schedule-assistant/
│   └── ...
│
├── agents/
│   └── registry.json          # Agent 注册表（可选）
│
└── backup-agents/             # 回收站（保留 7 天）
    ├── content-creator-20260315/
    └── ...
```

---

## 🔄 创建流程（7 步）

### 第 1 步：询问基础信息
- Agent 名称（标识符，不可改）
- 显示名（用户看到的名字）
- 人格设定（语气、风格、emoji）
- 职责描述（主要做什么）

### 第 2 步：能力配置
- 选择 Skills（从全局技能池）
- 选择模型（从全局模型池）

### 第 3 步：渠道配置引导 ⭐
- 询问发布到哪个渠道（Telegram / Discord / 飞书 / 仅主会话）
- 根据渠道类型引导用户提供必要信息：
  - **Telegram**: Bot Token（从 @BotFather 获取）
  - **Discord**: Bot Token + Guild ID + Channel ID
  - **飞书**: Webhook URL
  - **仅主会话**: 无需配置

### 第 4 步：定时任务配置
- 是否需要 cron/heartbeat
- 设置执行时间和频率

### 第 5 步：预览确认
- 展示所有配置
- 用户最终确认

### 第 6 步：执行创建
- 生成 workspace 文件（SOUL.md, USER.md, MEMORY.md, config.json）
- 更新主配置（添加 Bot Token 到 plugins）
- 自动启动 session

### 第 7 步：交付使用
- 告知用户如何访问新 Agent
- 提供测试建议

---

## 🎯 首期模板（5 个）

### 1️⃣ 📅 日程小管家
```yaml
名称：schedule-assistant
显示名：日程小管家 📅
职责：管理日历、提醒、待办、会议准备
Skills: cron, message
模型：bailian/qwen3.5-plus
渠道：Telegram
定时：每早 8 点推送今日日程，每晚 9 点复盘
```

### 2️⃣ ✍️ 内容创作助手
```yaml
名称：content-creator
显示名：创作小助手 ✍️
职责：写文章、润色、翻译、风格调整、多平台适配
Skills: humanizer, office, tts
模型：bailian/qwen3.5-plus
渠道：Telegram
```

### 3️⃣ 🔍 研究分析师
```yaml
名称：research-analyst
显示名：研究分析师 🔍
职责：深度调研、信息整理、报告生成、竞品分析
Skills: tavily-skill, web_fetch, pdf
模型：bailian/qwen3.5-plus
渠道：仅主会话（输出较长）
```

### 4️⃣ 📰 资讯监控员
```yaml
名称：news-monitor
显示名：资讯监控员 📰
职责：跟踪特定话题/关键词，定期汇总推送
Skills: tavily-skill, cron, message, web_fetch
模型：bailian/qwen3.5-plus
渠道：Telegram
定时：每 4-6 小时检查一次，汇总推送
```

### 5️⃣ 📊 用量监控官
```yaml
名称：usage-monitor
显示名：用量监控官 📊
职责：定期检查 Token 用量、API 配额、服务状态，异常时告警
Skills: bailian-usage, token-usage-analysis, cron, message
模型：bailian/qwen3.5-plus
渠道：Telegram
定时：每天检查 1-2 次，阈值告警
```

---

## 🛠️ 待实现功能清单

### Phase 1: 核心功能
- [ ] 创建器 Agent 的 workspace 搭建
- [ ] 对话引导逻辑实现
- [ ] workspace 文件生成模板
- [ ] 主配置修改逻辑（含备份/回滚）
- [ ] Session 自动启动
- [ ] 5 个模板文件准备

### Phase 2: 管理功能
- [ ] 查看列表/详情
- [ ] 修改配置
- [ ] 禁用/启用
- [ ] 删除（回收站模式）
- [ ] 健康检查

### Phase 3: 体验优化
- [ ] 错误处理完善
- [ ] 自然语言意图识别优化
- [ ] 创建后交付引导
- [ ] 文档和教程

---

## 📝 使用示例

### 创建新 Agent
```
用户：帮我创建一个日程助理
创建器：好的！我来帮你创建一个日程管理助手～

第一步：基础信息
- 你希望它叫什么名字？（英文标识符，如 schedule-assistant）
- 显示名是什么？（如"日程小管家 📅"）
- 你希望它是什么风格？（正式/活泼/温暖/专业）
- 主要职责是什么？（管理日历？提醒？待办？）

[逐步引导...]
```

### 查看已有 Agent
```
用户：看看我有哪些 Agent
创建器：
你目前有 3 个 Agent：

1. 📅 日程小管家 (schedule-assistant)
   状态：✅ 活跃 | 渠道：Telegram | 创建：2026-03-15

2. ✍️ 创作小助手 (content-creator)
   状态：✅ 活跃 | 渠道：Telegram | 创建：2026-03-15

3. 🔍 研究分析师 (research-analyst)
   状态：⏸️ 已禁用 | 渠道：仅主会话 | 创建：2026-03-14
```

### 健康检查
```
用户：检查创作助手是否正常
创建器：
✅ 健康检查结果：创作小助手

- Session 状态：✅ 活跃
- 渠道连接：✅ Telegram Bot 正常
- 文件完整性：✅ 所有必需文件存在

结论：运行正常，可以正常使用～
```

---

## 🔐 安全注意事项

1. **Bot Token 安全**：
   - 只存主配置，创建器只读
   - 不向用户索要明文私钥或助记词
   - 严禁外发敏感数据

2. **文件操作安全**：
   - 删除/覆盖前必须二次确认
   - 默认优先"移到回收站/备份"
   - 修改主配置前自动备份

3. **权限边界**：
   - 创建器不能访问其他 Agent 的 memory
   - 不能修改系统级配置
   - 破坏性操作必须用户确认

---

## 📚 参考资料

- OpenClaw 文档：`~/.openclaw/workspace/docs/`
- OpenClaw 官方文档：https://docs.openclaw.ai
- 社区：https://discord.com/invite/clawd
- 技能市场：https://clawhub.com

---

## 📅 更新日志

| 版本 | 日期 | 更新内容 |
|-----|------|---------|
| v1.0 | 2026-03-15 | 初始方案完成 |

---

**文档结束**
