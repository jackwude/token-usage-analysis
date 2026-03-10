#!/usr/bin/env python3
"""Merge xhs-keyword-search-export JSON outputs into one JSON/XLSX.

Designed for the MCP detail export (run_xhs_mcp_detail_export.py) outputs.

- Input: multiple JSON files (each contains: details[], summary, per_keyword, ...)
- Output: merged JSON + merged XLSX
- Dedup: by note_id (configurable)

This script does NOT fetch anything from XiaoHongShu; it only merges local files.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def _load_json(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_xlsx(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    # use same venv as other scripts (created on demand)
    try:
        import xlsxwriter  # type: ignore
    except Exception:
        raise RuntimeError("missing dependency: xlsxwriter")

    wb = xlsxwriter.Workbook(str(path))
    fmt_head = wb.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1, "text_wrap": True})
    fmt_cell = wb.add_format({"text_wrap": True, "valign": "top", "border": 1})
    fmt_link = wb.add_format({"color": "#0563C1", "underline": 1, "valign": "top", "border": 1})

    ws = wb.add_worksheet("details")

    # stable column order (superset)
    headers = [
        "keyword",
        "note_id",
        "xsec_token",
        "title",
        "author_nickname",
        "publish_time",
        "publish_ts",
        "note_type",
        "image_urls",
        "like_count",
        "comment_count",
        "collect_count",
        "url",
        "desc_full",
        "fetched_at",
        "neg_flag",
        "neg_score",
        "neg_labels",
        "neg_reasons",
        "error",
        "source_file",
        "source_group",
    ]

    for c, h in enumerate(headers):
        ws.write(0, c, h, fmt_head)

    for r, row in enumerate(rows, start=1):
        for c, h in enumerate(headers):
            v = row.get(h, "")
            if h == "url" and v:
                ws.write_url(r, c, str(v), fmt_link, string=str(v))
            else:
                ws.write(r, c, v if v is not None else "", fmt_cell)

    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(1, len(rows)), len(headers) - 1)

    ws2 = wb.add_worksheet("summary")
    ws2.write(0, 0, "generated_at", fmt_head)
    ws2.write(0, 1, datetime.now().isoformat(timespec="seconds"), fmt_cell)

    rowi = 2
    for k, v in summary.items():
        ws2.write(rowi, 0, k, fmt_head)
        ws2.write(rowi, 1, str(v), fmt_cell)
        rowi += 1

    wb.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inputs", action="append", required=True, help="Input JSON file; repeatable")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-xlsx", required=True)
    ap.add_argument("--dedup-key", default="note_id", help="Dedup key (default note_id)")
    ap.add_argument("--group", action="append", help="Optional group names aligned with --in order")
    args = ap.parse_args()

    inputs = [Path(x) for x in args.inputs]
    groups = (args.group or [])
    if groups and len(groups) != len(inputs):
        raise SystemExit("--group count must match --in count")

    seen: set[str] = set()
    merged: list[dict[str, Any]] = []

    for idx, p in enumerate(inputs):
        obj = _load_json(p)
        details = obj.get("details") or []
        if not isinstance(details, list):
            continue
        gname = groups[idx] if groups else f"G{idx+1}"
        for row in details:
            if not isinstance(row, dict):
                continue
            key = str(row.get(args.dedup_key) or "")
            if not key:
                continue
            if key in seen:
                continue
            seen.add(key)
            row2 = dict(row)
            row2["source_file"] = str(p.name)
            row2["source_group"] = gname
            merged.append(row2)

    summary = {
        "input_files": [str(p) for p in inputs],
        "total_merged": len(merged),
        "dedup_key": args.dedup_key,
        "unique_keys": len(seen),
    }

    out_json = Path(args.out_json)
    out_xlsx = Path(args.out_xlsx)

    _write_json(out_json, {"details": merged, "summary": summary})

    # xlsxwriter dependency: rely on the venv created by other scripts
    _write_xlsx(out_xlsx, merged, summary)

    print(str(out_json))
    print(str(out_xlsx))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
