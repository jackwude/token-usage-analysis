# GYING / 观影网 Profile 升级方案

## 现状结论

- 当前未发现现成的 `gying` 专用 Profile、cookies 文件或独立登录脚本。
- 现有 `gying-search` Skill 主要描述了搜索/提取/转存流程，但没有把“观影网登录态”作为长期主载体管理。
- 已初始化专用 Profile：
  - 目录：`~/.openclaw/chrome-profiles/gying`
  - 启动脚本：`~/.openclaw/scripts/start-gying-chrome.sh`
  - 调试端口：`9224`

## 推荐架构

### 主方案：Profile 持久化

固定使用：`~/.openclaw/chrome-profiles/gying`

用途：
- 保存观影网登录态
- 支撑影视搜索、详情页访问、资源区提取
- 供后续定时任务/自动化复用

### 兜底方案：不以 cookies 为主

除非后续实测发现观影网 cookies 单独复用也足够稳定，否则不建议先投入 cookies 注入方案。
原因：
- 登录网站通常不只依赖 cookie
- 长期自动化更需要完整浏览器上下文
- Profile 更适合无人值守任务

## 升级步骤

### 第 1 步：初始化专用 Profile（已完成）

执行：
```bash
bash ~/.openclaw/scripts/start-gying-chrome.sh
```

效果：
- 启动专用 Chrome
- 使用 `~/.openclaw/chrome-profiles/gying`
- 打开 `https://www.gying.net/`

### 第 2 步：首次种入登录态（待执行）

在专用 `gying` Profile 中：
1. 打开观影网
2. 完成登录
3. 进入搜索/详情页确认登录态已生效
4. 保留该 Profile 供后续复用

### 第 3 步：Skill 切换为 Profile 优先（待执行）

把 `skills/gying-search/SKILL.md` 改成：
1. 先启动 `start-gying-chrome.sh`
2. 固定使用 `~/.openclaw/chrome-profiles/gying`
3. 若已登录，直接执行搜索/详情/提取
4. 若未登录，再提示/执行登录

### 第 4 步：如存在定时任务，再切换 cron（待执行）

如果后续有观影网相关自动任务，应改成：
- 先启动 `gying` Profile
- 再进入 gying.net 执行任务
- 不再默认使用临时浏览器身份

### 第 5 步：纳入缓存清理（已完成）

已把 `gying` 纳入每周缓存清理：
- `Default/Cache`
- `Default/Code Cache`
- `Default/GPUCache`

注意：
- 清缓存不清登录态相关数据
- 仅做瘦身与稳定性维护

## 为什么推荐 Profile

因为观影网在你的工作流里：
- 需要登录
- 会反复使用
- 后续可能有自动化/定时任务
- 登录态是入口条件，而不是附加条件

这类站点更适合：
- 固定浏览器身份
- 长期复用同一个 Profile
- 必要时只做缓存治理，而不是反复重登

## 当前状态

- ✅ 已完成：专用 `gying` Profile 骨架初始化
- ⏳ 待完成：首次登录种入
- ⏳ 待完成：Skill 改成 Profile 优先
- ⏳ 待完成：如有需要，将定时任务切为 Profile 优先
