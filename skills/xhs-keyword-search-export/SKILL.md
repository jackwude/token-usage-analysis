---
name: xhs-keyword-search-export
description: |
  将“小红书关键词搜索抓取→结构化结果→导出 Excel/JSON”固化为可复用 Skill。
  当用户提出“小红书 关键词搜索 抓取/爬取/验证链路/导出Excel/按关键词分组/顺序执行/低频保守/每词取N条”等需求时使用。
---

# 小红书关键词搜索抓取 → 导出（Excel/JSON）

## 🚀 快速开始（推荐：后台子代理模式）

**长任务默认以子代理方式后台运行**，避免阻塞主会话。

### 方式 1：直接对我说命令（最简单）

```
帮我执行小红书关键词导出：
- 模式：详情导出
- 关键词文件：references/keywords.txt
- 每关键词目标：3 条
- 最近 7 天强校验
```

我会自动 spawn 子代理后台执行，并在完成后通知你。

### 方式 2：使用封装脚本

```bash
cd /Users/fx/.openclaw/workspace/skills/xhs-keyword-search-export

# 详情导出（后台运行）
python3 scripts/run_as_subagent.py \
  --mode detail \
  --keywords-file references/keywords.txt \
  --need-per-keyword 3 \
  --days 7

# 搜索列表导出（后台运行）
python3 scripts/run_as_subagent.py \
  --mode search \
  --keywords-file references/keywords.txt \
  --need-per-keyword 3
```

### 方式 3：直接运行底层脚本（前台阻塞，不推荐用于长任务）

仅用于调试或快速测试，长任务请用方式 1 或 2。

---

## 默认输入

- 所有脚本都通过 `--keywords-file` 读取关键词文件。
- 默认关键词文件：`references/keywords.txt`（逐行一个关键词；空行与 `#` 注释行会忽略）。

## 执行链路（固定）

本 Skill **固定只走 MCP 链路**，不再使用 CDP。

依赖：
- `mcporter` 已安装
- `mcporter` 中 `xiaohongshu` 已配置为：`http://127.0.0.1:18060/mcp`
- Docker Desktop 可用
- `xiaohongshu-mcp` 容器可启动且已具备登录态

## 运行时自动化（重要）

两个主脚本都会自动处理运行时环境：

- 运行前自动检查 Docker Desktop
- 如果 Docker 未启动：自动启动 Docker Desktop，并等待 Docker Engine 稳定可用
- 如果 `xiaohongshu-mcp` 容器未运行：自动启动容器
- 等待 `http://127.0.0.1:18060/mcp` 就绪后再执行抓取（就绪探测允许 4xx 响应，只要服务已活着即可继续）
- 首次 `search_feeds` 调用默认采用更长超时，并带一次重试，用于吸收 Docker / MCP 冷启动抖动

任务结束后执行 **强制回收（force-kill cleanup）**：
- 自动停止 `xiaohongshu-mcp` 容器
- 先执行 `quit app "Docker"`
- 等待数秒
- 若仍有残留进程，再定向强退 Docker Desktop / backend / helper 相关进程
- 目标是把 Docker Desktop 尽可能完整退出，避免长时间驻留占用内存

## 📜 脚本说明

### 封装脚本（推荐）

**`scripts/run_as_subagent.py`** - 子代理封装器

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode` | 导出模式：`detail`（详情）或 `search`（搜索列表） | 必填 |
| `--keywords-file` | 关键词文件路径 | 必填 |
| `--need-per-keyword` | 每关键词目标条数 | 2 |
| `--candidate-per-keyword` | 每关键词候选条数 | 10 |
| `--max-total` | 总条数上限 | 30 |
| `--days` | 详情模式：最近 N 天强校验 | 0（不校验） |
| `--negative-only` | 详情模式：仅负面内容 | 否 |
| `--out-json` | 详情模式：JSON 输出路径 | 自动生成 |
| `--out-xlsx` | 详情模式：Excel 输出路径 | 自动生成 |
| `--out-prefix` | 搜索模式：输出前缀 | 自动生成 |
| `--dry-run` | 仅打印命令，不执行 | 否 |

### 底层脚本（直接运行会阻塞）

#### 1) 搜索列表导出（快）

**`scripts/run_xhs_mcp_search_export.py`**

适合：关键词监控、快速拉候选、只需要标题/作者/互动数/封面/URL

特点：不进详情页、风控压力更小、速度更快（约 1-2 分钟/关键词）

**✅ 已增加进度播报**：每 25% 进度自动汇报

#### 2) 详情强校验导出（慢）

**`scripts/run_xhs_mcp_detail_export.py`**

适合：需要正文全量、详情页互动数据、最近 N 天强校验、负面过滤

特点：先搜索再逐条拉详情、可按 `note.time` 强校验、更保守的频控（约 3-6 分钟/关键词）

**✅ 已增加进度播报**：每 25% 进度自动汇报 + 失败详情提示

## 辅助脚本

- `scripts/run_xhs_negative_groups_plan.py`：大词库分组计划生成器；只生成分组文件和命令，不执行抓取
- `scripts/merge_xhs_exports.py`：合并多组 JSON 输出为总表

## 负面过滤

仅详情脚本支持负面过滤，**默认自动启用**。

**默认行为**：
- ✅ 自动过滤非负面内容
- ✅ 只保留负面笔记（评分 >= 阈值）
- ✅ 输出中包含 `neg_flag`, `neg_score`, `neg_labels`, `neg_reasons` 字段

**如需关闭负面过滤**：
```bash
python3 scripts/run_xhs_mcp_detail_export.py \
  --keywords-file references/keywords.txt \
  --no-negative-filter \
  --out-json output/all.json \
  --out-xlsx output/all.xlsx
```

**工作原理**：
- 在 `title + desc_full` 上做规则打分
- 仅保留负面内容（评分 >= 阈值）
- 如果负面内容不足，会标记为 `insufficient_negative`

**输出字段**：
- `neg_flag` - 是否负面（true/false）
- `neg_score` - 负面评分
- `neg_labels` - 命中的负面标签（逗号分隔）
- `neg_reasons` - 命中原因（逗号分隔）

**词典位置**：`references/negative_lexicon.json`

**适用场景**：
- 舆情监控（投诉、质量问题、差评等）
- 竞品负面分析
- 产品问题收集

## 常用参数

### 搜索列表脚本

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--sort-by` | **综合** | 排序方式：综合/最新/最热/最多点赞 |
| `--publish-time` | **一周内** | 发布时间筛选：一天内/一周内/一月内/三月内 |
| `--need-per-keyword` | 3 | 每关键词目标条数 |
| `--candidate-per-keyword` | 20 | 每关键词搜索候选条数 |
| `--max-total` | 200 | 总条数上限 |

### 详情导出脚本

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--sort-by` | **综合** | 排序方式：综合/最新/最热/最多点赞 |
| `--publish-time` | **一周内** | 搜索时筛选发布时间 |
| `--days` | **0（禁用）** | 详情强校验最近 N 天（0=不校验） |
| `--need-per-keyword` | 2 | 每关键词目标条数 |
| `--candidate-per-keyword` | 10 | 每关键词搜索候选条数 |
| `--negative-only` | **✅ 启用** | 只保留负面内容（默认开启） |
| `--max-detail-per-keyword` | 20 | 每关键词最多拉取详情条数 |
| `--auto-retry-ip-risk` | **✅ 启用** | 自动重试 IP 风控 |

## 输出

搜索列表导出：
- `<out-prefix>.json`
- `<out-prefix>.xlsx`

详情强校验导出：
- `--out-json <path>`
- `--out-xlsx <path>`

## 失败策略

- 单关键词失败：记录原因并继续下一个
- 搜索为空：标记为 `empty`
- 详情不足：标记为 `failed` 或 `insufficient_negative`
- 连续抓取异常时，返回已完成部分，不做激进重试

---

## 🛠️ 故障排查

### IP 风控（笔记不可访问）

**现象**：
- 搜索列表正常
- 详情抓取失败，错误："笔记不可访问：Sorry, This Page Isn't Available Right Now"
- 浏览器访问小红书显示"IP 存在风险"

**自动解决**（已内置）：
- 脚本会**自动检测 IP 风控**
- **自动重启 MCP 容器**刷新 IP
- **等待 10 秒后重试**
- 默认重试 1 次（可配置 `--max-ip-retry`）

**手动解决**：
```bash
# 重启容器
docker restart xiaohongshu-mcp

# 等待 10 秒
sleep 10

# 重新运行任务
```

### Docker 无法启动

**现象**：`Docker Desktop 未启动` 或 `Docker Engine 未稳定就绪`

**解决**：
1. 手动打开 Docker Desktop 应用
2. 等待底部状态栏显示 `Docker Desktop is running`
3. 重新运行任务

### MCP 服务连接失败

**现象**：`xiaohongshu MCP 未在超时内就绪` 或 `connection refused`

**解决**：
```bash
# 检查容器状态
docker ps | grep xiaohongshu-mcp

# 如果容器未运行，手动启动
docker start xiaohongshu-mcp

# 如果容器不存在，重新拉取
docker pull xpzouying/xiaohongshu-mcp:latest
docker run -d --name xiaohongshu-mcp -p 18060:18060 xpzouying/xiaohongshu-mcp:latest
```

### 登录态失效

**现象**：搜索结果为空，或返回 `401 Unauthorized`

**解决**：
1. 访问 https://www.xiaohongshu.com 确认是否需要重新登录
2. 登录成功后，重新运行任务（MCP 容器会复用浏览器 Cookie）

### mcporter 未安装

**现象**：`command not found: mcporter`

**解决**：
```bash
npm install -g mcporter
mcporter config add xiaohongshu http://127.0.0.1:18060/mcp
```

### xlsxwriter 缺失

**现象**：`missing dependency: xlsxwriter`

**解决**：脚本会自动创建虚拟环境并安装，无需手动操作。如失败则手动安装：
```bash
pip install xlsxwriter
```

### 输出文件未生成

**检查**：
1. 确认输出目录存在且有写权限
2. 检查任务是否完整执行完成（看日志最后是否有 `✅ 任务完成`）
3. 失败时会生成部分结果，检查 JSON 中的 `summary` 字段

---

## 📊 进度播报说明

**搜索列表导出**：
```
[1/5] 开始处理关键词：XXX (目标 3 条)
  [XXX] 搜索列表进度：5/20 (已获取 1 条)
  [XXX] 搜索列表进度：10/20 (已获取 2 条)
  [XXX] ✅ 完成：获取 3 条
```

**详情导出**：
```
[1/5] 开始处理关键词：XXX (候选 10 条，目标 2 条)
  [XXX] 详情抓取进度：1/10 (已获取 0 条，已拉详情 1 条)
  [XXX] 详情抓取进度：5/10 (已获取 1 条，已拉详情 5 条)
  [XXX] 详情抓取失败：5f3a2b1c... - timeout
[1/5] XXX -> kept=2 fetched=8 status=success
```

**播报频率**：每 25% 进度自动播报一次，关键节点（开始/结束/失败）必报。
