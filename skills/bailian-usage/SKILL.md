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

### 方案 A：Profile 持久化（推荐 ✅）

**首次配置后，以后无需登录**

配置方法：
```bash
# 1. 创建 Profile 目录
mkdir -p ~/.openclaw/chrome-profiles/bailian

# 2. 用 browser 工具打开百炼控制台并手动登录
# 3. 登录后关闭页面，状态会自动保存
```

**优势**：
- ✅ 一次登录，长期有效
- ✅ 包含所有 Cookies（包括 HttpOnly）
- ✅ 支持 LocalStorage/SessionStorage
- ✅ 无需每次输入密码

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

### 方案 A：Profile 持久化（推荐）

1. **打开浏览器** → 访问百炼控制台（自动登录）
2. **查看订阅** → 点击"我的订阅"tab
3. **提取信息** → 获取套餐详情和用量
4. **关闭页面** → 清理浏览器资源（省内存）
5. **返回结果** → 格式化输出

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

1. **优先使用 Profile 方案** - 更高效稳定
2. **Profile 目录位置** - `~/.openclaw/chrome-profiles/bailian/`
3. **完成后关闭页面** - 避免浏览器资源占用
4. **登录失败处理** - Profile 失效时切换到账号密码方案
5. **用量刷新时间** - 可能滞后，以页面显示为准
6. **定期清理浏览器** - 防止页面堆积导致超时

## 快捷命令

- "查百炼额度" → 调用本 Skill
- "看看阿里云还剩多少额度" → 调用本 Skill
- "百炼用量情况" → 调用本 Skill
- "查 Token" → 调用本 Skill
- "百炼套餐用量" → 调用本 Skill

## 相关文件

- **Skill 目录**: `~/.openclaw/workspace/skills/bailian-usage/`
- **Profile 目录**: `~/.openclaw/chrome-profiles/bailian/`
- **账号信息**: `~/.openclaw/workspace/TOOLS.md`
