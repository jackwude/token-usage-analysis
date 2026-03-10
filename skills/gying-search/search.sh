#!/bin/bash
# 观影网影视资源搜索调试辅助脚本 v0.4.3
# 用法：bash search.sh <关键词> [数量]
# 说明：用于生成“可用入口 + 操作提示”，不是完整自动化引擎。

set -euo pipefail

KEYWORD="${1:-}"
LIMIT="${2:-5}"

if [ -z "$KEYWORD" ]; then
  echo "❌ 请提供搜索关键词"
  echo "用法：bash $0 <关键词> [返回数量，默认 5]"
  echo "示例：bash $0 模范出租车"
  exit 1
fi

# 观影网近期搜索路由：/s/1---1/<关键词>
# 注意：站点会弹出遮罩层(popup-overlay)拦截点击；必要时先按 ESC 或关闭弹窗。
ENCODED=$(python3 - <<PY
import sys, urllib.parse
print(urllib.parse.quote(sys.argv[1]))
PY
"$KEYWORD")

HOME_URL="https://www.gying.net/"
SEARCH_URL="https://www.gying.net/s/1---1/${ENCODED}"

echo "🎬 关键词：$KEYWORD"
echo "📺 首页：$HOME_URL"
echo "🔎 搜索页：$SEARCH_URL"
echo "⏳ 预计耗时：30-60 秒（取决于页面弹窗/加载/资源数量）"
echo ""
echo "----------------------------------------"
echo "🤖 建议执行步骤（稳定版）："
echo "0) 先用 gying 专用 Profile 启动 Chrome：bash ~/.openclaw/scripts/start-gying-chrome.sh"
echo "1) 打开 $HOME_URL，确认已登录；如有弹窗遮罩，先按 ESC 或关闭弹窗"
echo "2) 用首页搜索框搜索“$KEYWORD”（不要强依赖旧 /s?q= 路由）"
echo "   - 若你想直接打开搜索结果页，可用：$SEARCH_URL"
echo "3) 进入最匹配的详情页（URL 通常是 /ac/<id>）"
echo "4) 切到「百度网盘」Tab（若有）；提取前 $LIMIT 条网盘链接："
echo "   - 优先 pan.baidu.com（百度网盘）"
echo "   - 若无百度，则退回 pan.quark.cn（夸克网盘）"
echo "5) 同时抓：豆瓣评分/提取码/更新时间（如页面提供）"
echo "----------------------------------------"
echo ""
echo "📋 输出格式："
echo "🎬 影视资源搜索结果：《$KEYWORD》"
echo ""
echo "1. 标题：xxx"
echo "   豆瓣评分：8.2 / 暂无评分"
echo "   百度网盘：https://pan.baidu.com/s/xxx（优先）/ 或 夸克网盘：https://pan.quark.cn/s/xxx"
echo "   提取码：1234 / 无"
echo "   更新时间：2026-03-10 / 未知"
