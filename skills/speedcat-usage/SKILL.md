# SpeedCat 签到 + 用量查询 Skill

查询 SpeedCat 闪电猫机场的套餐用量、余额、到期时间等信息，并执行每日签到。

## 触发条件

用户提到以下关键词时激活：
- "查 speedcat 用量"
- "SpeedCat 用量"
- "闪电猫用量"
- "speedcat 余额"
- "看看 speedcat 情况"
- "speedcat 签到"
- "闪电猫签到"
- "执行 speedcat 签到任务"

## 前置准备

### Agent Browser State 持久化（优先使用）
优先使用 Agent Browser 的登录态保存：
- Session 名：`speedcat`
- State 文件：`~/.openclaw/browser-states/speedcat.json`
- 机制：`state load` → 打开用户页 → 必要时登录 → `state save`

### Profile/Cookies（仅作兜底）
- Profile：`~/.openclaw/chrome-profiles/speedcat/`
- Cookies：`~/.openclaw/cookies/speedcat.json`
- 仅在 state 方案异常时临时回退，不作为主链路。

### 账号信息（Profile 掉登录时的备选）
优先从 macOS Keychain 读取；必要时再参考 `TOOLS.md`：
```markdown
## 🔐 SpeedCat 账号
- **网址**: https://speedcat.co/user
- **邮箱**: xxx@xxx.com
- **密码**: xxx
```

## 执行流程

### 🚀 推荐模式（优先）：Agent Browser State 持久化
1. **加载状态**：`agent-browser --session speedcat state load ~/.openclaw/browser-states/speedcat.json`（若文件存在）
2. **访问用户页**：打开 `https://speedcat.co/user`
3. **检查是否已登录**：若进入用户中心，直接继续
4. **如未登录**：执行完整登录流程（见下方）
5. **登录成功后保存状态**：`state save` 覆盖更新
6. **任务结束再保存一次**：保证下次复用最新状态

### 📝 完整登录流程（State 失效时）
1. **通过验证**：若遇到访问验证页，点击"我不是恶意刷站"
2. **登录**：
   - 优先从 macOS Keychain 读取账号密码
   - 若 Keychain 不可用，再从 `TOOLS.md` 读取 SpeedCat 账号（邮箱 + 密码）
   - 填写邮箱和密码并点击登录
3. **登录成功后立即保存 state**：更新 `~/.openclaw/browser-states/speedcat.json`
4. **后续任务优先复用 state**：不再默认依赖 Profile

### 🪂 兜底模式：Profile/Cookies
1. 当 `state load + 自动登录` 连续失败时，临时回退到 Profile 或 cookies
2. 回退成功后，仍需重新保存 Agent Browser state，恢复主链路

### 📊 查询和签到
6. **执行签到**：点击"每日签到"按钮（页面左侧菜单或首页）
7. **确认签到**：等待"签到成功"弹窗出现，点击"OK"确认
8. **提取信息**：从页面获取用量数据
   - 套餐名称（如"迷你猫"）
   - 到期时间/剩余天数
   - 流量重置时间
   - 剩余流量
   - 今日已用流量
   - 在线 IP 数
   - 上次使用时间
   - 钱包余额
   - 累计返利金额
9. **关闭浏览器**：完成后关闭本次打开的页面；如需保活专用 Profile 供后续自动化复用，可只关闭标签页、保留浏览器实例
10. **返回结果**：格式化输出用量信息

## 稳定性策略（让每次输出尽量一致）

SpeedCat 页面即使"内容看起来固定"，也常包含 **动态字段**（如"上次使用时间/在线 IP/一些展示格式"），再加上 LLM 生成式表述，容易导致每次输出不一致。

本 Skill 的稳定输出规则：

1. **只输出可确定的、直接抓取到的字段**；抓不到就填 `-`，不猜测、不补全。
2. **统一单位与精度**：流量统一为 **GB**，保留 **2 位小数**；金额保留 **2 位小数**。
3. **固定字段顺序**（下方模板顺序不变）。
4. **动态字段默认不纳入"核心结果"**：
   - `在线 IP`、`上次使用时间` 属于波动项：放在"附加信息"里（可选），避免干扰对比。
5. **用量分析只做规则判断，不做自由发挥**（防止措辞漂移）：
   - 剩余流量 ≥ 50 GB → `✅ 充足`
   - 10–50 GB → `⚠️ 关注`
   - < 10 GB → `❌ 紧张`
6. **Cookies 注入失败时自动回退**：如注入后未检测到登录态，自动执行完整登录流程

## 输出格式（稳定版）

```markdown
## 📊 SpeedCat 用量详情

**套餐：** {plan_name} | 剩余 **{days_left} 天**（{expire_date} 到期）
**流量重置：** {reset_date}

**流量使用：**
- 剩余流量：**{remaining_gb} GB**
- 今日已用：**{used_today_gb} GB**

**账户信息：**
- 钱包余额：**¥ {wallet_cny}**（累计返利：¥ {rebate_cny}）

**用量判断：** {traffic_status}

### 附加信息（波动项）
- 在线 IP：{online_ip}
- 上次使用：{last_used}
- 今日签到：{checkin_status}
```

## 注意事项

1. **优先使用 Agent Browser state 持久化**：固定使用 session `speedcat` + state 文件 `~/.openclaw/browser-states/speedcat.json`
2. **Profile/Cookies 只作兜底**：state 主链路失败时临时回退，回退成功后要重新 `state save`
3. **Keychain 优先于 TOOLS.md**：优先读 macOS Keychain 中的 SpeedCat 账号密码
4. 必须先通过访问验证（点击"我不是恶意刷站"按钮）
5. **签到成功后会弹出"签到成功"对话框**，必须点击"OK"确认后才能继续
6. 完成后关闭本次打开页面；如果任务链需要继续复用登录态，可保留专用浏览器实例
7. 流量单位可能是 GB 或 MB，需统一转换；统一输出为 GB（保留 2 位小数）
8. 金额统一输出为 CNY（保留 2 位小数）；若页面无货币符号也按数值处理
9. 每日只能签到一次，如已签到会显示"明日再来"
10. 若页面包含时间戳/广告/推荐位导致抓取文本漂移，优先 **定位到明确的字段标签/卡片** 再读值，不要整段复制摘要
11. 定期清理 `Cache` / `Code Cache` / `GPUCache`，但不要主动删除登录态相关数据

## 性能优化

| 模式 | 耗时 | 触发条件 |
|------|------|----------|
| **推荐模式**（Profile 复用） | ~5-12 秒 | Profile 已登录 |
| **兜底模式**（Cookies 注入） | ~5-10 秒 | 仅临时应急 |
| **完整模式**（重新登录） | ~20-40 秒 | Profile 掉登录 / 首次初始化 |

**推荐模式流程**：
1. 启动专用 Profile → 2. 打开页面 → 3. 验证登录态 → 4. 提取数据/执行签到

**兜底模式流程**：
1. 读取 cookies 文件 → 2. 打开页面 → 3. 注入 cookies → 4. 刷新验证 → 5. 失败则回退

**完整模式流程**：
1. 打开专用 Profile 页面 → 2. 通过验证 → 3. 登录 → 4. 保留 Profile → 5. 可选更新 cookies → 6. 提取数据

## 快捷命令

- "查 speedcat 用量" → 调用本 Skill
- "闪电猫还剩多少流量" → 调用本 Skill
- "speedcat 余额" → 调用本 Skill
- "speedcat 签到" → 调用本 Skill（执行签到 + 查询用量）
- "闪电猫签到" → 调用本 Skill
- "执行 speedcat 签到任务" → 调用本 Skill
- "看看 speedcat 情况" → 调用本 Skill

## 相关文档

- Cookies 配置说明：`~/.openclaw/docs/speedcat-login-setup.md`
- Cookies 文件：`~/.openclaw/cookies/speedcat.json`
- 注入脚本：`~/.openclaw/scripts/inject-speedcat-cookies.sh`
