---
name: xhs-keyword-search-export
description: |
  将“小红书关键词搜索抓取→结构化结果→导出 Excel/JSON”固化为可复用 Skill。
  当用户提出“小红书 关键词搜索 抓取/爬取/验证链路/导出Excel/按关键词分组/顺序执行/低频保守/每词取N条”等需求时使用。
---

# 小红书关键词搜索抓取 → 导出（Excel/JSON）

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

## 主入口选择

### 1) 搜索列表导出（快）

使用：`scripts/run_xhs_mcp_search_export.py`

适合：
- 关键词监控
- 快速拉一批候选内容
- 只需要标题 / 作者 / 互动数 / 封面 / URL
- 不要求精确发布时间

特点：
- 不进详情页
- 风控压力更小
- 速度更快

示例：

```bash
cd /Users/fx/.openclaw/workspace/skills/xhs-keyword-search-export
python3 scripts/run_xhs_mcp_search_export.py \
  --keywords-file references/keywords.txt \
  --need-per-keyword 3 \
  --out-prefix /Users/fx/.openclaw/workspace/out/xhs_search_list
```

### 2) 详情强校验导出（慢）

使用：`scripts/run_xhs_mcp_detail_export.py`

适合：
- 需要正文全量
- 需要详情页互动数据
- 需要按最近 N 天做强校验
- 需要负面过滤

特点：
- 先搜索，再逐条拉详情
- 可按 `note.time` 做最近 N 天强校验
- 可自动补齐每关键词样本数
- 默认更保守的频控

示例：

```bash
cd /Users/fx/.openclaw/workspace/skills/xhs-keyword-search-export
python3 scripts/run_xhs_mcp_detail_export.py \
  --keywords-file references/keywords.txt \
  --days 7 \
  --candidate-per-keyword 10 \
  --need-per-keyword 2 \
  --out-json /Users/fx/.openclaw/workspace/xhs_mcp_detail_week.json \
  --out-xlsx /Users/fx/.openclaw/workspace/xhs_mcp_detail_week.xlsx
```

## 辅助脚本

- `scripts/run_xhs_negative_groups_plan.py`：大词库分组计划生成器；只生成分组文件和命令，不执行抓取
- `scripts/merge_xhs_exports.py`：合并多组 JSON 输出为总表

## 负面过滤

仅详情脚本支持 `--negative-only`。

启用后会在 `title + desc_full` 上做规则打分，并输出：
- `neg_flag`
- `neg_score`
- `neg_labels`
- `neg_reasons`

词典位置：`references/negative_lexicon.json`

## 常用参数

搜索列表脚本常用：
- `--need-per-keyword`
- `--candidate-per-keyword`
- `--max-total`
- `--sleep-min`
- `--sleep-max`

详情脚本常用：
- `--days`
- `--candidate-per-keyword`
- `--need-per-keyword`
- `--max-total`
- `--negative-only`
- `--max-detail-per-keyword`
- `--limit-keywords`
- `--search-timeout-ms`
- `--search-retry`
- `--search-retry-sleep`

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
