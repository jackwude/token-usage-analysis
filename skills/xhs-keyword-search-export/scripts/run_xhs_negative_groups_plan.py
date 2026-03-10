#!/usr/bin/env python3
"""Plan/group runner for negative-only MCP export.

This script helps split a big keyword list into groups (e.g., 10 per group) and
prints (or optionally executes) per-group commands with cool-down intervals.

By default it only prints a run plan (no execution), per your safety preference.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from datetime import datetime


def _read_keywords(path: Path) -> list[str]:
    kws: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        kws.append(s)
    return kws


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords-file", required=True)
    ap.add_argument("--group-size", type=int, default=10)
    ap.add_argument("--interval-min", type=int, default=10, help="minutes between groups")
    ap.add_argument(
        "--out-dir",
        default="",
        help="输出目录（可选）。为空则自动使用 /Users/fx/.openclaw/workspace/out/xhs_neg_groups/<YYYYMMDD_HHMMSS>/",
    )
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--need-per-keyword", type=int, default=5)
    ap.add_argument("--max-detail-per-keyword", type=int, default=20)
    ap.add_argument("--candidate-per-keyword", type=int, default=10)
    args = ap.parse_args()

    kw_path = Path(args.keywords_file)
    kws = _read_keywords(kw_path)
    n = len(kws)
    if n == 0:
        raise SystemExit("no keywords")

    groups = math.ceil(n / args.group_size)

    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("/Users/fx/.openclaw/workspace/out/xhs_neg_groups") / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Total keywords: {n}")
    print(f"Group size: {args.group_size} => groups: {groups}")
    print(f"Interval between groups: {args.interval_min} minutes")
    print()

    merge_args = []

    for gi in range(groups):
        start = gi * args.group_size
        end = min(n, (gi + 1) * args.group_size)
        group_kws = kws[start:end]
        gname = f"G{gi+1:02d}"
        gfile = out_dir / f"keywords_{gname}.txt"
        gfile.write_text("\n".join(group_kws) + "\n", encoding="utf-8")

        out_json = out_dir / f"xhs_negative_{gname}.json"
        out_xlsx = out_dir / f"xhs_negative_{gname}.xlsx"
        merge_args.append((out_json, gname))

        cmd = (
            "python3 scripts/run_xhs_mcp_detail_export.py "
            f"--keywords-file {gfile} "
            f"--days {args.days} "
            f"--candidate-per-keyword {args.candidate_per_keyword} "
            f"--need-per-keyword {args.need_per_keyword} "
            f"--negative-only --max-detail-per-keyword {args.max_detail_per_keyword} "
            f"--out-json {out_json} --out-xlsx {out_xlsx}"
        )

        print(f"[{gname}] {start+1}-{end} ({len(group_kws)} keywords)")
        print(f"  keywords_file: {gfile}")
        print(f"  command: {cmd}")
        if gi < groups - 1:
            print(f"  then wait: {args.interval_min} minutes")
        print()

    # print merge command template
    merged_json = out_dir / "xhs_negative_merged.json"
    merged_xlsx = out_dir / "xhs_negative_merged.xlsx"
    print("Merge command (after all groups finished):")
    parts = ["python3 scripts/merge_xhs_exports.py"]
    for p, g in merge_args:
        parts.append(f"  --in {p} --group {g}")
    parts.append(f"  --out-json {merged_json} --out-xlsx {merged_xlsx}")
    print("\\n".join(parts))
    print()

    print("NOTE: This script only generated group keyword files and printed commands. It did NOT execute them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
