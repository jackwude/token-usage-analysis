#!/bin/bash
# xhs-export - 小红书关键词导出快捷命令
# 用法：./xhs-export.sh --mode detail --keywords-file refs/keywords.txt --need-per-keyword 3

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 默认参数
MODE=""
KEYWORDS_FILE=""
NEED_PER_KEYWORD=2
CANDIDATE_PER_KEYWORD=10
MAX_TOTAL=30
DAYS=0
NEGATIVE_ONLY=""
OUT_JSON=""
OUT_XLSX=""
OUT_PREFIX=""
DRY_RUN=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --keywords-file)
            KEYWORDS_FILE="$2"
            shift 2
            ;;
        --need-per-keyword)
            NEED_PER_KEYWORD="$2"
            shift 2
            ;;
        --candidate-per-keyword)
            CANDIDATE_PER_KEYWORD="$2"
            shift 2
            ;;
        --max-total)
            MAX_TOTAL="$2"
            shift 2
            ;;
        --days)
            DAYS="$2"
            shift 2
            ;;
        --negative-only)
            NEGATIVE_ONLY="--negative-only"
            shift
            ;;
        --out-json)
            OUT_JSON="$2"
            shift 2
            ;;
        --out-xlsx)
            OUT_XLSX="$2"
            shift 2
            ;;
        --out-prefix)
            OUT_PREFIX="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "小红书关键词导出工具"
            echo ""
            echo "用法：$0 --mode <detail|search> --keywords-file <路径> [选项]"
            echo ""
            echo "必填参数:"
            echo "  --mode              导出模式：detail (详情) 或 search (搜索列表)"
            echo "  --keywords-file     关键词文件路径（每行一个关键词）"
            echo ""
            echo "常用选项:"
            echo "  --need-per-keyword  每关键词目标条数 (默认：2)"
            echo "  --candidate-per-keyword  每关键词候选条数 (默认：10)"
            echo "  --max-total         总条数上限 (默认：30)"
            echo "  --days              详情模式：最近 N 天强校验 (默认：0 不校验)"
            echo "  --negative-only     详情模式：仅负面内容"
            echo "  --out-json          详情模式：JSON 输出路径 (默认：自动生成)"
            echo "  --out-xlsx          详情模式：Excel 输出路径 (默认：自动生成)"
            echo "  --out-prefix        搜索模式：输出前缀 (默认：自动生成)"
            echo "  --dry-run           仅打印命令，不执行"
            echo "  -h, --help          显示帮助"
            echo ""
            echo "示例:"
            echo "  # 详情导出（最近 7 天，每词 3 条）"
            echo "  $0 --mode detail --keywords-file references/keywords.txt --need-per-keyword 3 --days 7"
            echo ""
            echo "  # 搜索列表导出（每词 5 条）"
            echo "  $0 --mode search --keywords-file references/keywords.txt --need-per-keyword 5"
            echo ""
            echo "  # 负面内容抓取（仅详情模式）"
            echo "  $0 --mode detail --keywords-file references/keywords.txt --need-per-keyword 5 --negative-only"
            exit 0
            ;;
        *)
            echo "未知参数：$1"
            echo "使用 -h 或 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 参数校验
if [[ -z "$MODE" ]]; then
    echo "❌ 错误：--mode 是必填参数"
    echo "使用 -h 或 --help 查看帮助"
    exit 1
fi

if [[ -z "$KEYWORDS_FILE" ]]; then
    echo "❌ 错误：--keywords-file 是必填参数"
    echo "使用 -h 或 --help 查看帮助"
    exit 1
fi

if [[ ! -f "$KEYWORDS_FILE" ]]; then
    echo "❌ 错误：关键词文件不存在：$KEYWORDS_FILE"
    exit 1
fi

# 构建命令
CMD="python3 scripts/run_as_subagent.py"
CMD="$CMD --mode $MODE"
CMD="$CMD --keywords-file $KEYWORDS_FILE"
CMD="$CMD --need-per-keyword $NEED_PER_KEYWORD"
CMD="$CMD --candidate-per-keyword $CANDIDATE_PER_KEYWORD"
CMD="$CMD --max-total $MAX_TOTAL"

if [[ "$DAYS" -gt 0 ]]; then
    CMD="$CMD --days $DAYS"
fi

if [[ -n "$NEGATIVE_ONLY" ]]; then
    CMD="$CMD $NEGATIVE_ONLY"
fi

if [[ -n "$OUT_JSON" ]]; then
    CMD="$CMD --out-json $OUT_JSON"
fi

if [[ -n "$OUT_XLSX" ]]; then
    CMD="$CMD --out-xlsx $OUT_XLSX"
fi

if [[ -n "$OUT_PREFIX" ]]; then
    CMD="$CMD --out-prefix $OUT_PREFIX"
fi

if [[ "$DRY_RUN" == true ]]; then
    CMD="$CMD --dry-run"
fi

# 执行
echo "🦞 小红书关键词导出任务"
echo "   模式：$MODE"
echo "   关键词文件：$KEYWORDS_FILE"
echo "   每关键词目标：$NEED_PER_KEYWORD 条"
echo ""

eval $CMD
