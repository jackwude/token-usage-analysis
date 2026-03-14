#!/usr/bin/env python3
"""
xhs-keyword-search-export 子代理封装器

用途：
- 将长任务以子代理方式后台运行，避免阻塞主会话
- 自动处理任务分派和结果通知

使用方式：
1. 直接运行（会自动 spawn 子代理）：
   python3 scripts/run_as_subagent.py --mode detail --keywords-file refs/keywords.txt --need-per-keyword 3

2. 或在主会话中用 message 命令触发（推荐）：
   /sessions_spawn task="执行小红书关键词导出，参数：..."

参数：
- --mode: detail | search （detail=详情导出，search=搜索列表导出）
- --keywords-file: 关键词文件路径
- 其他参数透传给底层导出脚本
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DETAIL_SCRIPT = SCRIPT_DIR / "run_xhs_mcp_detail_export.py"
SEARCH_SCRIPT = SCRIPT_DIR / "run_xhs_mcp_search_export.py"


def build_command(mode: str, args: argparse.Namespace) -> list[str]:
    """构建底层导出脚本的命令。"""
    if mode == "detail":
        cmd = [sys.executable, str(DETAIL_SCRIPT)]
    elif mode == "search":
        cmd = [sys.executable, str(SEARCH_SCRIPT)]
    else:
        raise ValueError(f"未知模式：{mode}")

    # 透传参数
    if hasattr(args, "keywords_file") and args.keywords_file:
        cmd += ["--keywords-file", args.keywords_file]
    if hasattr(args, "need_per_keyword") and args.need_per_keyword:
        cmd += ["--need-per-keyword", str(args.need_per_keyword)]
    if hasattr(args, "candidate_per_keyword") and args.candidate_per_keyword:
        cmd += ["--candidate-per-keyword", str(args.candidate_per_keyword)]
    if hasattr(args, "max_total") and args.max_total:
        cmd += ["--max-total", str(args.max_total)]
    if hasattr(args, "days") and args.days:
        cmd += ["--days", str(args.days)]
    if hasattr(args, "negative_only") and args.negative_only:
        cmd += ["--negative-only"]
    if hasattr(args, "out_json") and args.out_json:
        cmd += ["--out-json", args.out_json]
    if hasattr(args, "out_xlsx") and args.out_xlsx:
        cmd += ["--out-xlsx", args.out_xlsx]
    if hasattr(args, "out_prefix") and args.out_prefix:
        cmd += ["--out-prefix", args.out_prefix]

    return cmd


def generate_task_description(mode: str, args: argparse.Namespace) -> str:
    """生成任务描述，用于子代理任务。"""
    mode_name = "详情导出" if mode == "detail" else "搜索列表导出"
    kw_file = args.keywords_file or "未指定"
    need = args.need_per_keyword or "默认"

    return f"执行小红书关键词{mode_name}任务：关键词文件={kw_file}, 每关键词目标={need}条"


def main() -> int:
    ap = argparse.ArgumentParser(description="xhs 导出任务子代理封装器")
    ap.add_argument("--mode", required=True, choices=["detail", "search"], help="导出模式")
    ap.add_argument("--keywords-file", required=True, help="关键词文件路径")
    ap.add_argument("--need-per-keyword", type=int, default=2, help="每关键词目标条数")
    ap.add_argument("--candidate-per-keyword", type=int, default=10, help="每关键词候选条数")
    ap.add_argument("--max-total", type=int, default=30, help="总条数上限")
    ap.add_argument("--days", type=int, default=0, help="详情模式：最近 N 天强校验")
    ap.add_argument("--negative-only", action="store_true", help="详情模式：仅负面内容")
    ap.add_argument("--out-json", help="详情模式：JSON 输出路径")
    ap.add_argument("--out-xlsx", help="详情模式：Excel 输出路径")
    ap.add_argument("--out-prefix", help="搜索模式：输出前缀")
    ap.add_argument("--dry-run", action="store_true", help="仅打印命令，不执行")

    args = ap.parse_args()

    # 检查是否在子代理环境中运行
    is_subagent = "OPENCLAW_SUBAGENT" in str(subprocess.os.environ.get("OPENCLAW_RUNTIME", ""))

    # 生成输出文件名（如果未指定）- 必须在 build_command 之前
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.mode == "detail":
        if not args.out_json:
            args.out_json = f"/Users/fx/.openclaw/workspace/out/xhs_detail_{ts}.json"
        if not args.out_xlsx:
            args.out_xlsx = f"/Users/fx/.openclaw/workspace/out/xhs_detail_{ts}.xlsx"
    else:
        if not args.out_prefix:
            args.out_prefix = f"/Users/fx/.openclaw/workspace/out/xhs_search_{ts}"

    task_desc = generate_task_description(args.mode, args)
    cmd = build_command(args.mode, args)

    if args.dry_run:
        print(f"[dry-run] 任务描述：{task_desc}")
        print(f"[dry-run] 执行命令：{' '.join(cmd)}")
        return 0

    print(f"📚 小红书关键词导出任务")
    print(f"   模式：{args.mode}")
    print(f"   关键词文件：{args.keywords_file}")
    print(f"   每关键词目标：{args.need_per_keyword}条")
    print(f"   输出：{args.out_json if args.mode == 'detail' else args.out_prefix + '.json'}")
    print()

    # 执行任务
    print(f"🚀 开始执行...")
    print(f"   命令：{' '.join(cmd)}")
    print()
    print(f"--- 进度播报 ---")
    sys.stdout.flush()

    try:
        # 使用 capture_output=False 让底层脚本的 print 直接显示
        result = subprocess.run(cmd, capture_output=False, text=True, check=False)
        if result.returncode == 0:
            print()
            print(f"✅ 任务完成！")
            if args.mode == "detail":
                print(f"   JSON: {args.out_json}")
                print(f"   Excel: {args.out_xlsx}")
            else:
                print(f"   JSON: {args.out_prefix}.json")
                print(f"   Excel: {args.out_prefix}.xlsx")
            return 0
        else:
            print()
            print(f"❌ 任务失败，退出码：{result.returncode}")
            return 1
    except Exception as e:
        print()
        print(f"❌ 任务异常：{e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
