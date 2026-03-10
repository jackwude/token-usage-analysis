#!/usr/bin/env python3
"""xhs keyword search -> export (json/xlsx)

Design goals:
- 顺序执行关键词，不并发
- 低频保守：每个关键词间 sleep
- 每关键词最多抓取 N 条（默认 3）
- 总量上限（默认 30）
- 不重复同一 link
- 连续 3 个关键词失败则终止

Data source:
- Uses xiaohongshu-skills CLI: scripts/cli.py search-feeds
- By default only list results (no get-feed-detail)

"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


XHS_REPO = Path("/Users/fx/.openclaw/workspace/skills/xiaohongshu-skills")
XHS_VENV_PY = XHS_REPO / ".venv" / "bin" / "python"
XHS_CLI = XHS_REPO / "scripts" / "cli.py"


@dataclass
class Item:
    keyword: str
    title: str
    excerpt: str
    author: str
    publish_time: str
    link: str


def _read_keywords(path: str) -> list[str]:
    kws: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        kws.append(s)
    return kws


def _run_search(keyword: str, *, host: str, port: int, sort_by: str, publish_time: str) -> list[dict[str, Any]]:
    if not XHS_VENV_PY.exists():
        raise RuntimeError(f"xhs venv python not found: {XHS_VENV_PY}")
    if not XHS_CLI.exists():
        raise RuntimeError(f"xhs cli not found: {XHS_CLI}")

    cmd = [
        str(XHS_VENV_PY),
        str(XHS_CLI),
        "--host",
        host,
        "--port",
        str(port),
        "search-feeds",
        "--keyword",
        keyword,
    ]
    if sort_by:
        cmd += ["--sort-by", sort_by]
    if publish_time:
        cmd += ["--publish-time", publish_time]

    p = subprocess.run(
        cmd,
        cwd=str(XHS_REPO),
        capture_output=True,
        text=True,
        timeout=90,
    )
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "unknown error").strip())

    data = json.loads(p.stdout)
    feeds = data.get("feeds") or []
    if not isinstance(feeds, list):
        return []
    return feeds


def _extract_item(feed: dict[str, Any], keyword: str) -> Item:
    # Feed.to_dict() typical fields: id, xsecToken, displayTitle, type, user{nickname}, ...
    title = str(feed.get("displayTitle") or feed.get("display_title") or feed.get("title") or "").strip()

    author = ""
    user = feed.get("user")
    if isinstance(user, dict):
        author = str(user.get("nickname") or user.get("nickName") or user.get("name") or "").strip()

    # search-feeds list typically has no excerpt / publish_time
    excerpt = ""
    publish_time = ""

    note_id = str(feed.get("id") or feed.get("noteId") or feed.get("note_id") or "").strip()
    link = f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else ""

    return Item(
        keyword=keyword,
        title=title,
        excerpt=excerpt,
        author=author,
        publish_time=publish_time,
        link=link,
    )


def _write_json(path: str, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_xlsx(path: str, rows: list[Item], summary: dict[str, Any], per_keyword: dict[str, int]) -> None:
    # Use xlsxwriter inside xhs venv if available.
    try:
        import xlsxwriter  # type: ignore
    except Exception:
        # best-effort: import with xhs venv by spawning a helper
        raise RuntimeError(
            "missing dependency: xlsxwriter. Install it in xhs venv: "
            "/opt/homebrew/bin/uv pip install XlsxWriter (run under xhs venv)"
        )

    wb = xlsxwriter.Workbook(path)
    fmt_head = wb.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1})
    fmt_cell = wb.add_format({"text_wrap": True, "valign": "top", "border": 1})
    fmt_link = wb.add_format({"color": "#0563C1", "underline": 1, "valign": "top", "border": 1})

    # results sheet
    ws = wb.add_worksheet("results")
    headers = ["keyword", "title", "excerpt", "author", "publish_time", "link"]
    for c, h in enumerate(headers):
        ws.write(0, c, h, fmt_head)

    for r, it in enumerate(rows, start=1):
        ws.write(r, 0, it.keyword, fmt_cell)
        ws.write(r, 1, it.title, fmt_cell)
        ws.write(r, 2, it.excerpt, fmt_cell)
        ws.write(r, 3, it.author, fmt_cell)
        ws.write(r, 4, it.publish_time, fmt_cell)
        if it.link:
            ws.write_url(r, 5, it.link, fmt_link, string=it.link)
        else:
            ws.write(r, 5, "", fmt_cell)

    ws.set_column(0, 0, 18)
    ws.set_column(1, 1, 42)
    ws.set_column(2, 2, 50)
    ws.set_column(3, 3, 16)
    ws.set_column(4, 4, 16)
    ws.set_column(5, 5, 58)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(1, len(rows)), len(headers) - 1)

    # summary sheet
    ws2 = wb.add_worksheet("summary")
    ws2.write(0, 0, "generated_at", fmt_head)
    ws2.write(0, 1, datetime.now().isoformat(timespec="seconds"), fmt_cell)

    rowi = 2
    for k in ["executed_keywords", "successful_keywords", "failed_keywords", "total_items", "unique_links"]:
        if k in summary:
            ws2.write(rowi, 0, k, fmt_head)
            ws2.write(rowi, 1, summary.get(k), fmt_cell)
            rowi += 1

    rowi += 2
    ws2.write(rowi, 0, "per_keyword_count", fmt_head)
    rowi += 1
    ws2.write(rowi, 0, "keyword", fmt_head)
    ws2.write(rowi, 1, "count", fmt_head)
    rowi += 1
    for kw, ct in per_keyword.items():
        ws2.write(rowi, 0, kw, fmt_cell)
        ws2.write(rowi, 1, ct, fmt_cell)
        rowi += 1

    ws2.set_column(0, 0, 30)
    ws2.set_column(1, 1, 18)

    wb.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords-file", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--sort-by", default="综合")
    ap.add_argument("--publish-time", default="一周内")
    ap.add_argument("--max-per-keyword", type=int, default=3)
    ap.add_argument("--max-total", type=int, default=30)
    ap.add_argument("--sleep-min", type=float, default=2.0)
    ap.add_argument("--sleep-max", type=float, default=4.0)
    ap.add_argument("--out-prefix", required=True)

    args = ap.parse_args()

    keywords = _read_keywords(args.keywords_file)
    results: dict[str, list[dict[str, Any]]] = {}
    failures: dict[str, str] = {}

    rows: list[Item] = []
    per_keyword: dict[str, int] = {}
    seen_links: set[str] = set()

    consecutive_fail = 0
    total = 0

    for idx, kw in enumerate(keywords, start=1):
        if total >= args.max_total:
            break

        try:
            feeds = _run_search(
                kw,
                host=args.host,
                port=args.port,
                sort_by=args.sort_by,
                publish_time=args.publish_time,
            )

            items: list[dict[str, Any]] = []
            for f in feeds:
                it = _extract_item(f, kw)
                if not it.link or it.link in seen_links:
                    continue
                seen_links.add(it.link)

                items.append({
                    "keyword": it.keyword,
                    "title": it.title,
                    "excerpt": it.excerpt,
                    "author": it.author,
                    "publish_time": it.publish_time,
                    "link": it.link,
                })
                rows.append(it)
                total += 1

                if len(items) >= args.max_per_keyword or total >= args.max_total:
                    break

            results[kw] = items
            per_keyword[kw] = len(items)
            consecutive_fail = 0

        except Exception as e:
            failures[kw] = str(e)
            per_keyword[kw] = 0
            consecutive_fail += 1
            if consecutive_fail >= 3:
                break

        # sleep between keywords (avoid high-frequency)
        if idx < len(keywords):
            # deterministic jitter without random module
            span = max(0.0, args.sleep_max - args.sleep_min)
            sleep_s = args.sleep_min + (span * ((idx % 3) / 2.0) if span else 0.0)
            time.sleep(sleep_s)

    summary = {
        "executed_keywords": len(per_keyword),
        "successful_keywords": sum(1 for k, v in per_keyword.items() if v > 0),
        "failed_keywords": len(failures),
        "total_items": len(rows),
        "unique_links": len(seen_links),
        "failed_keywords_details": failures,
    }

    payload = {
        "results": results,
        "summary": summary,
    }

    out_json = args.out_prefix + ".json"
    out_xlsx = args.out_prefix + ".xlsx"

    _write_json(out_json, payload)

    # write xlsx using xhs venv python
    # run current script with xhs venv is recommended; but we try locally.
    _write_xlsx(out_xlsx, rows, summary, per_keyword)

    print(out_json)
    print(out_xlsx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
