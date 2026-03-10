#!/bin/bash
# 观影网影视资源搜索脚本 v0.4.1
# 用法：bash search.sh <关键词> [数量]
# 功能：搜索影视资源，提取豆瓣评分和百度网盘链接

KEYWORD="${1:-}"
LIMIT="${2:-10}"

if [ -z "$KEYWORD" ]; then
    echo "❌ 请提供搜索关键词"
    echo "用法：bash $0 <关键词> [返回数量，默认 10]"
    echo "示例：bash $0 模范出租车"
    exit 1
fi

echo "🎬 正在搜索：$KEYWORD"
echo "⏳ 预计耗时：30-60 秒"
echo ""

# 使用 browser 工具进行搜索和提取
SEARCH_URL="https://www.gying.net/s?q=$(echo $KEYWORD | sed 's/ /+/g')"
DETAIL_URL="https://www.gying.net/ac/9wAd"

echo "📺 搜索链接：$SEARCH_URL"
echo ""
echo "----------------------------------------"
echo "🤖 Agent 执行步骤："
echo "1. 使用 browser 打开 $SEARCH_URL"
echo "2. 点击第一个搜索结果进入详情页"
echo "3. 切换到「百度网盘」标签"
echo "4. 提取前 $LIMIT 个有效链接（标题 + 链接 + 提取码）"
echo "5. 按更新时间排序，优先返回最新资源"
echo "----------------------------------------"
echo ""
echo "📋 输出格式："
echo "🎬 影视资源搜索结果：《$KEYWORD》"
echo ""
echo "1. 【标题】⭐ 豆瓣评分：X.X"
echo "   🔗 https://pan.baidu.com/s/xxx"
echo ""
echo "... (共 X 条链接)"
echo ""
echo "💡 提示：优先选择「今天」更新的链接"

exit 0
