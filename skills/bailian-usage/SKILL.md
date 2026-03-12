# bailian-usage Skill

查询阿里云百炼 Coding Plan 套餐用量和有效期信息。

## 模型配置

**默认模型：** qwen3.5-plus（如需更换，可在调用时通过 `--model` 参数指定）

## 触发条件

用户提到以下关键词时激活：
- "查百炼套餐"
- "百炼用量"
- "百炼额度"
- "阿里云百炼"
- "Coding Plan"
- "看看套餐情况"

## 前置准备

### 方案 A：Agent Browser 显式 State 持久化（推荐 ✅）

**主链路（强制）：state load -> 访问页面 -> 必要时登录 -> state save -> 复测免登**

配置约定：
- Session：`bailian`
- State 文件：`~/.openclaw/browser-states/bailian.json`

**执行要求（重要）**：
- 主链路必须使用显式 `state load/save`，不要把“openclaw 默认 profile 自动复用”当作 state 成功。
- 登录后必须做一次复测：关闭当前会话并重开页面，确认不再跳登录页。

**优势**：
- ✅ 登录态保存/加载是显式动作，稳定且可观测
- ✅ 易于自动化编排（失效检测、自动回写）
- ✅ 一站点一状态文件，维护更轻
### 方案 B：账号密码登录（备选）

账号信息存储在 `TOOLS.md` 中，格式：
```markdown
## 🔐 阿里云百炼账号
- **网址**: https://bailian.console.aliyun.com/cn-beijing/?tab=coding-plan#/efm/index
- **账号**: xxx@qq.com
- **密码**: xxx
```

**适用场景**：Profile 失效时作为备选方案

## 执行流程

### 方案 A：Agent Browser 显式 State 持久化（推荐）

1. **加载 state**（若存在）→ `state load ~/.openclaw/browser-states/bailian.json`
2. **打开页面** → 访问百炼控制台
3. **检查登录态** → 若未登录则走账号密码登录
4. **进入“我的订阅”** → 提取套餐详情和用量
5. **保存 state** → `state save` 覆盖更新
6. **复测免登（必须）** → 关闭当前会话后重开同页面，确认不再跳登录
7. **关闭页面** → 清理浏览器资源（省内存）
8. **返回结果** → 格式化输出
### 方案 B：账号密码登录（备选）

1. **读取账号信息** → 从 `TOOLS.md` 获取百炼账号密码
2. **打开浏览器** → 访问百炼控制台
3. **登录** → 点击登录 → 账密登录 → 输入账号密码 → 登录
4. **查看订阅** → 点击左侧"我的订阅"tab
5. **提取信息** → 从页面获取套餐详情
6. **关闭浏览器** → 必须关闭所有浏览器标签页（激进省内存策略）
7. **返回结果** → 格式化输出套餐信息

## 输出格式（精简版）

```markdown
## 📊 百炼 Coding Plan 套餐详情

**套餐状态：** ✅ 生效中 | 剩余 **xx 天**（YYYY-MM-DD 到期）  
**自动续费：** ❌ 未开启 / ✅ 已开启

**用量消耗：**
- 最后统计时间：YYYY-MM-DD HH:mm:ss
- 近 5 小时：**xx%**（YYYY-MM-DD HH:mm:ss **重置**）
- 近一周：**xx%**（YYYY-MM-DD HH:mm:ss **重置**）
- 近一月：**xx%**（YYYY-MM-DD HH:mm:ss **重置**）

**可用模型：** 千问系列 / 智谱 / Kimi / MiniMax

---

### 💡 用量分析
- ✅ 用量充足 / ⚠️ 用量紧张 / ❌ 用量不足
- 到期提醒（如适用）
```

## 注意事项

1. **优先使用 state 方案** - session `bailian` + `~/.openclaw/browser-states/bailian.json`
2. **完成后关闭页面** - 避免浏览器资源占用
3. **登录失败处理** - state 失效时切换账号密码登录并重新 `state save`
4. **高风控场景** - 若触发短信/二次验证，需人工补一次验证后再持久化
5. **用量刷新时间** - 可能滞后，以页面显示为准
6. **Profile 仅兜底** - 仅在显式 state 连续失败时临时回退；回退成功后必须重新 `state save` 并做免登复测

## 快捷命令

- "查百炼额度" → 调用本 Skill
- "看看阿里云还剩多少额度" → 调用本 Skill
- "百炼用量情况" → 调用本 Skill
- "百炼 Token" → 调用本 Skill
- "百炼套餐用量" → 调用本 Skill

## 边界说明

- 本 Skill **只负责阿里云百炼 / Coding Plan / 套餐 / 额度 / 百炼 Token** 相关查询。
- 像“查 Token 用量”“Token 消耗”“过去 24 小时 Token 用量”这类**未明确提到百炼**的说法，**不应**由本 Skill 处理，应转交 `token-usage-analysis`。

## 相关文件

- **Skill 目录**: `~/.openclaw/workspace/skills/bailian-usage/`
- **Profile 目录**: `~/.openclaw/chrome-profiles/bailian/`
- **账号信息**: `~/.openclaw/workspace/TOOLS.md`
