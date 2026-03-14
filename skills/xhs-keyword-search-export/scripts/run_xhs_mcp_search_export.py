#!/usr/bin/env python3
"""xhs MCP keyword search -> export (json/xlsx)

目的
- 只导出搜索列表结果（不进详情页），速度快、风控压力小
- 适合做“关键词监控/舆情扫描/线索池”

数据源
- mcporter + xiaohongshu-mcp（server 名称 xiaohongshu）
  - xiaohongshu.search_feeds(keyword, filters)

特性
- 顺序执行关键词，不并发
- 全局速率限制器（跨关键词统一控速）
- 去重：以 note_id 去重（同一笔记不会重复导出）
- 每关键词补齐到 N 条（默认 3），不足则返回已获取条数
- 输出 Excel/JSON

注意
- 搜索列表通常缺少精确发布时间；如需“最近 N 天强校验”，请用详情脚本 run_xhs_mcp_detail_export.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from xhs_mcp_runtime import cleanup_xhs_mcp, ensure_xhs_mcp, runtime_summary


VENV_DIR = Path.home() / ".agent-reach" / "tools" / "xhs-keyword-search-export" / "venv"
_NEXT_ALLOWED_TS: float = 0.0


def _ensure_xlsxwriter() -> None:
    try:
        import xlsxwriter  # noqa: F401
        return
    except Exception:
        pass

    vpy = VENV_DIR / "bin" / "python"
    if not vpy.exists():
        VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)

    subprocess.run([str(vpy), "-m", "pip", "install", "-U", "pip", "wheel"], check=False)
    subprocess.run([str(vpy), "-m", "pip", "install", "xlsxwriter"], check=True)

    os.execv(str(vpy), [str(vpy), *sys.argv])


def _sleep_gate(idx: int, min_s: float, max_s: float) -> None:
    """全局速率限制器 + 抖动 sleep（用于 MCP 调用间隔）。"""
    global _NEXT_ALLOWED_TS
    span = max(0.0, max_s - min_s)
    seed = int(time.time()) + idx * 97
    frac = (seed % 1000) / 1000.0
    target = min_s + span * frac

    now = time.time()
    if _NEXT_ALLOWED_TS > now:
        time.sleep(_NEXT_ALLOWED_TS - now)

    time.sleep(target)
    _NEXT_ALLOWED_TS = time.time()


def _read_keywords(path: str) -> list[str]:
    kws: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        kws.append(s)
    return kws


def _mcporter_call(selector: str, *, timeout_ms: int = 90000, retries: int = 1, retry_sleep: float = 8.0) -> Any:
    # mcporter call <selector> --output json --timeout <ms>
    # 使用 --args 传递 JSON 参数（这是 xiaohongshu-mcp 的正确调用方式）
    # 解析 selector 格式：search_feeds(keyword: 'xxx') -> {"keyword": "xxx"}
    import re
    match = re.search(r'search_feeds\(keyword:\s*([\'"])([^\'"]+)\1\)', selector)
    if not match:
        raise RuntimeError(f"无法解析 selector: {selector}")
    keyword = match.group(2)
    args_json = json.dumps({"keyword": keyword})
    
    # 计算正确的配置文件路径：scripts -> skill -> skills -> workspace
    script_dir = Path(__file__).resolve().parent  # scripts/
    skill_dir = script_dir.parent  # xhs-keyword-search-export/
    skills_dir = skill_dir.parent  # skills/
    workspace_dir = skills_dir.parent  # .openclaw/workspace/
    config_path = workspace_dir / "config" / "mcporter.json"
    print(f"  [DEBUG] config_path: {config_path}, exists: {config_path.exists()}")
    last_err = ""
    for attempt in range(retries + 1):
        # 使用 --config 参数指定配置文件路径
        cmd = ["mcporter", "--config", str(config_path), "call", "xiaohongshu.search_feeds", "--args", args_json, "--output", "json", "--timeout", str(timeout_ms)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=max(30, timeout_ms // 1000 + 20))
        out = (p.stdout or "").strip()
        err = (p.stderr or "").strip()
        if out:
            try:
                return json.loads(out)
            except Exception:
                last_err = f"mcporter output not json: {out[:200]}, stderr: {err[:500]}"
        else:
            last_err = f"empty output, stderr: {err[:500]}"

        print(f"  [DEBUG] 尝试{attempt+1}: {last_err[:100]}")

        transient = any(k in last_err.lower() for k in ["timed out", "timeout", "offline", "connection refused", "bad gateway"])
        if attempt < retries and transient:
            time.sleep(retry_sleep)
            continue
        raise RuntimeError(last_err)

    raise RuntimeError(last_err or "mcporter call failed")


@dataclass
class Row:
    keyword: str
    note_id: str
    xsec_token: str
    title: str
    author_nickname: str
    note_type: str
    like_count: str
    comment_count: str
    collect_count: str
    cover_url: str
    url: str
    fetched_at: str


def _extract_row(feed: dict[str, Any], keyword: str) -> Row | None:
    note_id = str(feed.get("id") or "")
    xsec_token = str(feed.get("xsecToken") or "")
    note_card = feed.get("noteCard") or {}

    title = str(note_card.get("displayTitle") or "").strip()
    user = note_card.get("user") or {}
    author = str(user.get("nickname") or user.get("nickName") or "").strip()

    note_type = str(note_card.get("type") or feed.get("modelType") or "").strip()

    interact = note_card.get("interactInfo") or {}
    like_count = str(interact.get("likedCount") or "")
    comment_count = str(interact.get("commentCount") or "")
    collect_count = str(interact.get("collectedCount") or "")

    cover = note_card.get("cover") or {}
    cover_url = str(cover.get("urlDefault") or cover.get("urlPre") or "").strip()

    if not note_id:
        return None

    url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}" if xsec_token else f"https://www.xiaohongshu.com/explore/{note_id}"

    return Row(
        keyword=keyword,
        note_id=note_id,
        xsec_token=xsec_token,
        title=title,
        author_nickname=author,
        note_type=note_type,
        like_count=like_count,
        comment_count=comment_count,
        collect_count=collect_count,
        cover_url=cover_url,
        url=url,
        fetched_at=datetime.now().isoformat(timespec="seconds"),
    )


def _write_json(path: str, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_xlsx(path: str, rows: list[Row], summary: dict[str, Any], per_keyword: dict[str, Any]) -> None:
    _ensure_xlsxwriter()
    import xlsxwriter  # type: ignore

    Path(path).parent.mkdir(parents=True, exist_ok=True)

    wb = xlsxwriter.Workbook(path)
    fmt_head = wb.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1, "text_wrap": True})
    fmt_cell = wb.add_format({"text_wrap": True, "valign": "top", "border": 1})
    fmt_link = wb.add_format({"color": "#0563C1", "underline": 1, "valign": "top", "border": 1})

    ws = wb.add_worksheet("results")
    headers = [
        "keyword",
        "note_id",
        "xsec_token",
        "title",
        "author_nickname",
        "note_type",
        "like_count",
        "comment_count",
        "collect_count",
        "cover_url",
        "url",
        "fetched_at",
    ]
    for c, h in enumerate(headers):
        ws.write(0, c, h, fmt_head)

    for r, row in enumerate(rows, start=1):
        ws.write(r, 0, row.keyword, fmt_cell)
        ws.write(r, 1, row.note_id, fmt_cell)
        ws.write(r, 2, row.xsec_token, fmt_cell)
        ws.write(r, 3, row.title, fmt_cell)
        ws.write(r, 4, row.author_nickname, fmt_cell)
        ws.write(r, 5, row.note_type, fmt_cell)
        ws.write(r, 6, row.like_count, fmt_cell)
        ws.write(r, 7, row.comment_count, fmt_cell)
        ws.write(r, 8, row.collect_count, fmt_cell)
        ws.write(r, 9, row.cover_url, fmt_cell)
        if row.url:
            ws.write_url(r, 10, row.url, fmt_link, string=row.url)
        else:
            ws.write(r, 10, "", fmt_cell)
        ws.write(r, 11, row.fetched_at, fmt_cell)

    ws.set_column(0, 0, 18)
    ws.set_column(1, 2, 26)
    ws.set_column(3, 3, 40)
    ws.set_column(4, 5, 16)
    ws.set_column(6, 8, 14)
    ws.set_column(9, 10, 60)
    ws.set_column(11, 11, 20)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(1, len(rows)), len(headers) - 1)

    ws2 = wb.add_worksheet("summary")
    ws2.write(0, 0, "generated_at", fmt_head)
    ws2.write(0, 1, datetime.now().isoformat(timespec="seconds"), fmt_cell)

    rowi = 2
    for k, v in summary.items():
        if k == "failed_keywords_details":
            continue
        ws2.write(rowi, 0, k, fmt_head)
        ws2.write(rowi, 1, str(v), fmt_cell)
        rowi += 1

    rowi += 2
    ws2.write(rowi, 0, "per_keyword", fmt_head)
    rowi += 1
    ws2.write(rowi, 0, "keyword", fmt_head)
    ws2.write(rowi, 1, "count", fmt_head)
    ws2.write(rowi, 2, "attempted", fmt_head)
    ws2.write(rowi, 3, "reason", fmt_head)
    rowi += 1
    for kw, info in per_keyword.items():
        ws2.write(rowi, 0, kw, fmt_cell)
        ws2.write(rowi, 1, str(info.get("count", "")), fmt_cell)
        ws2.write(rowi, 2, str(info.get("attempted", "")), fmt_cell)
        ws2.write(rowi, 3, str(info.get("reason", "")), fmt_cell)
        rowi += 1

    wb.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords-file", required=True)
    ap.add_argument("--sort-by", default="综合", help="排序方式：综合/最新/最热/最多点赞（默认综合）")
    ap.add_argument("--publish-time", default="一周内", help="发布时间筛选（如'一周内'，留空表示不筛选；默认一周内）")
    ap.add_argument("--need-per-keyword", type=int, default=3)
    ap.add_argument("--candidate-per-keyword", type=int, default=20)
    ap.add_argument("--max-total", type=int, default=200)

    ap.add_argument("--sleep-min", type=float, default=1.2, help="全局限速最小间隔")
    ap.add_argument("--sleep-max", type=float, default=2.5, help="全局限速最大间隔")

    ap.add_argument("--out-prefix", required=True)

    args = ap.parse_args()

    try:
        ensure_xhs_mcp()
        print(f"[runtime] {runtime_summary()}")

        keywords = _read_keywords(args.keywords_file)

        rows: list[Row] = []
        per_keyword: dict[str, dict[str, Any]] = {}
        failures: dict[str, str] = {}

        seen_note_ids: set[str] = set()

        total = 0
        total_keywords = len(keywords)
        for kidx, kw in enumerate(keywords, start=1):
            if total >= args.max_total:
                break

            got = 0
            attempted = 0
            reason = ""

            try:
                print(f"[{kidx}/{total_keywords}] 开始处理关键词：{kw} (目标{args.need_per_keyword}条)")
                print(f"  [DEBUG] 调用 search_feeds(keyword: {kw!r})")

                _sleep_gate(kidx, args.sleep_min, args.sleep_max)
                data = _mcporter_call(f"search_feeds(keyword: {kw!r})", timeout_ms=120000, retries=1, retry_sleep=10.0)
                print(f"  [DEBUG] 返回数据 keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                feeds = data.get("feeds") or []
                if not isinstance(feeds, list) or not feeds:
                    raise RuntimeError(f"搜索结果为空 data={str(data)[:200]}")

                candidates = feeds[: max(1, args.candidate_per_keyword)]
                total_candidates = len(candidates)
                progress_interval = max(1, total_candidates // 4)  # 每 25% 播报一次

                for cand_idx, f in enumerate(candidates, start=1):
                    if got >= args.need_per_keyword or total >= args.max_total:
                        break
                    attempted += 1

                    # 进度播报
                    if cand_idx % progress_interval == 0 or cand_idx == total_candidates:
                        print(f"  [{kw}] 搜索列表进度：{cand_idx}/{total_candidates} (已获取{got}条)")

                    row = _extract_row(f, kw)
                    if not row:
                        continue
                    if row.note_id in seen_note_ids:
                        continue
                    seen_note_ids.add(row.note_id)

                    rows.append(row)
                    got += 1
                    total += 1

                per_keyword[kw] = {"count": got, "attempted": attempted, "reason": reason}
                print(f"  [{kw}] ✅ 完成：获取{got}条")

            except Exception as e:
                failures[kw] = str(e)
                per_keyword[kw] = {"count": got, "attempted": attempted, "reason": str(e)}
                print(f"  [{kw}] ❌ 失败：{str(e)[:80]}")

        summary = {
            "executed_keywords": len(per_keyword),
            "successful_keywords": sum(1 for v in per_keyword.values() if v.get("count", 0) > 0),
            "failed_keywords": len(failures),
            "total_items": len(rows),
            "unique_note_ids": len(seen_note_ids),
            "failed_keywords_details": failures,
            "need_per_keyword": args.need_per_keyword,
            "candidate_per_keyword": args.candidate_per_keyword,
            "filters": {"sort_by": args.sort_by, "publish_time": args.publish_time},
        }

        payload = {
            "results": [asdict(r) for r in rows],
            "summary": summary,
            "per_keyword": per_keyword,
        }

        out_json = args.out_prefix + ".json"
        out_xlsx = args.out_prefix + ".xlsx"

        _write_json(out_json, payload)
        _write_xlsx(out_xlsx, rows, summary, per_keyword)

        print(out_json)
        print(out_xlsx)
        return 0
    finally:
        cleanup_xhs_mcp()


if __name__ == "__main__":
    raise SystemExit(main())
