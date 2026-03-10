#!/usr/bin/env python3
"""xhs detail export: search-feeds -> get-feed-detail -> JSON/Excel

保守低频策略：
- 每个关键词 search-feeds 取候选池（默认前 10 条）
- 逐条调用 get-feed-detail 获取详情，并以详情页 time 做“最近 N 天”强校验（默认 7 天）
- keyword 之间 sleep 2~4s
- get-feed-detail 后额外 sleep 10~15s
- 连续 3 次失败则终止

输出：
- JSON: details + summary
- Excel: Sheet1=details, Sheet2=summary
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any


XHS_REPO = Path("/Users/fx/.openclaw/workspace/skills/xiaohongshu-skills")
XHS_VENV_PY = XHS_REPO / ".venv" / "bin" / "python"
XHS_CLI = XHS_REPO / "scripts" / "cli.py"


@dataclass
class DetailRow:
    keyword: str
    noteId: str
    title: str
    desc: str
    type: str
    time: int
    time_beijing: str
    ipLocation: str
    author_nickname: str
    likedCount: str
    collectedCount: str
    commentCount: str
    sharedCount: str
    imageCount: int
    link: str
    error: str = ""


def _read_keywords(path: str) -> list[str]:
    kws: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        kws.append(s)
    return kws


def _run_search(keyword: str, *, host: str, port: int, sort_by: str, publish_time: str) -> list[dict[str, Any]]:
    """执行 search-feeds 命令。"""
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


def _run_detail(feed_id: str, xsec_token: str, *, host: str, port: int) -> dict[str, Any]:
    """执行 get-feed-detail 命令。"""
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
        "get-feed-detail",
        "--feed-id",
        feed_id,
        "--xsec-token",
        xsec_token,
    ]

    p = subprocess.run(
        cmd,
        cwd=str(XHS_REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "unknown error").strip())

    return json.loads(p.stdout)


def _format_beijing_time(ts: int) -> str:
    """把 Unix 时间戳转换为北京时间字符串。

    兼容：
    - 秒级：1710000000
    - 毫秒级：1710000000000
    """
    if not ts:
        return ""
    # heuristics: treat >= 10^12 as ms
    if ts >= 1_000_000_000_000:
        ts = ts // 1000
    try:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(ZoneInfo("Asia/Shanghai"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def _extract_detail_from_result(detail_data: dict[str, Any], keyword: str) -> DetailRow:
    """从 get-feed-detail 结果提取字段。"""
    note = detail_data.get("note", {})
    user = note.get("user", {})
    interact = note.get("interactInfo", {})
    image_list = note.get("imageList", [])

    note_id = str(note.get("noteId") or "")
    title = str(note.get("title") or "").strip()
    desc = str(note.get("desc") or "")  # 正文全量（不截断）
    note_type = str(note.get("type") or "")
    time_val = int(note.get("time") or 0)
    time_bj = _format_beijing_time(time_val)
    ip_location = str(note.get("ipLocation") or "")
    author_nickname = str(user.get("nickname") or user.get("nick_name") or "")

    liked_count = str(interact.get("likedCount") or "")
    collected_count = str(interact.get("collectedCount") or "")
    comment_count = str(interact.get("commentCount") or "")
    shared_count = str(interact.get("sharedCount") or "")
    image_count = len(image_list) if isinstance(image_list, list) else 0

    # 构建 link
    xsec_token = detail_data.get("xsecToken") or note.get("xsecToken") or ""
    if xsec_token:
        link = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}"
    else:
        link = f"https://www.xiaohongshu.com/explore/{note_id}"

    return DetailRow(
        keyword=keyword,
        noteId=note_id,
        title=title,
        desc=desc,
        type=note_type,
        time=time_val,
        time_beijing=time_bj,
        ipLocation=ip_location,
        author_nickname=author_nickname,
        likedCount=liked_count,
        collectedCount=collected_count,
        commentCount=comment_count,
        sharedCount=shared_count,
        imageCount=image_count,
        link=link,
    )


def _check_error(detail_data: dict[str, Any]) -> str | None:
    """检查详情页是否“硬失败”。

    仅将以下情况视为硬失败（按你的要求）：
    - 扫码验证
    - 不可访问/仅作者可见/私密/内容不存在/已失效等
    - 已删除/违规删除

    注意：不再因为标题/描述里出现“异常/失败/错误”等词就跳过，避免误伤正常内容。
    """
    note = detail_data.get("note")
    if not note:
        return "无 note 数据"

    title = str(note.get("title", "") or "")
    desc = str(note.get("desc", "") or "")
    text = title + "\n" + desc

    hard_keywords = [
        "扫码", "扫码查看", "打开小红书App扫码",
        "不可访问", "无法浏览", "仅作者可见", "私密", "内容不存在", "笔记不存在", "已失效",
        "已删除", "因违规已被删除", "该内容因违规已被删除",
    ]
    for kw in hard_keywords:
        if kw and kw in text:
            return f"硬失败关键词命中：{kw}"

    # 如果 title 和 desc 都为空，通常也是异常（保守起见视为硬失败）
    if not title.strip() and not desc.strip():
        return "title 和 desc 均为空"

    return None


def _write_json(path: str, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_xlsx(path: str, rows: list[DetailRow], summary: dict[str, Any], per_keyword: dict[str, Any]) -> None:
    """使用 XlsxWriter 写入 Excel。"""
    try:
        import xlsxwriter
    except ImportError:
        # 尝试用 venv 安装
        subprocess.run(
            [str(XHS_VENV_PY), "-m", "pip", "install", "XlsxWriter", "-q"],
            capture_output=True,
        )
        try:
            import xlsxwriter
        except ImportError:
            raise RuntimeError("无法安装 XlsxWriter")

    wb = xlsxwriter.Workbook(path)
    fmt_head = wb.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1, "text_wrap": True})
    fmt_cell = wb.add_format({"text_wrap": True, "valign": "top", "border": 1})
    fmt_link = wb.add_format({"color": "#0563C1", "underline": 1, "valign": "top", "border": 1})
    fmt_error = wb.add_format({"text_wrap": True, "valign": "top", "border": 1, "font_color": "red"})

    # Sheet1: details
    ws = wb.add_worksheet("details")
    headers = [
        "keyword", "noteId", "title", "desc", "type", "time", "time_beijing", "ipLocation",
        "author_nickname", "likedCount", "collectedCount", "commentCount",
        "sharedCount", "imageCount", "link", "error"
    ]
    for c, h in enumerate(headers):
        ws.write(0, c, h, fmt_head)

    for r, row in enumerate(rows, start=1):
        ws.write(r, 0, row.keyword, fmt_cell)
        ws.write(r, 1, row.noteId, fmt_cell)
        ws.write(r, 2, row.title, fmt_cell)
        ws.write(r, 3, row.desc, fmt_cell)
        ws.write(r, 4, row.type, fmt_cell)
        ws.write(r, 5, row.time, fmt_cell)
        ws.write(r, 6, row.time_beijing, fmt_cell)
        ws.write(r, 7, row.ipLocation, fmt_cell)
        ws.write(r, 8, row.author_nickname, fmt_cell)
        ws.write(r, 9, row.likedCount, fmt_cell)
        ws.write(r, 10, row.collectedCount, fmt_cell)
        ws.write(r, 11, row.commentCount, fmt_cell)
        ws.write(r, 12, row.sharedCount, fmt_cell)
        ws.write(r, 13, row.imageCount, fmt_cell)
        if row.link:
            ws.write_url(r, 14, row.link, fmt_link, string=row.link)
        else:
            ws.write(r, 14, "", fmt_cell)
        if row.error:
            ws.write(r, 15, row.error, fmt_error)
        else:
            ws.write(r, 15, "", fmt_cell)

    # 设置列宽
    ws.set_column(0, 0, 20)  # keyword
    ws.set_column(1, 1, 22)  # noteId
    ws.set_column(2, 2, 40)  # title
    ws.set_column(3, 3, 60)  # desc
    ws.set_column(4, 4, 10)  # type
    ws.set_column(5, 5, 16)  # time
    ws.set_column(6, 6, 20)  # time_beijing
    ws.set_column(7, 7, 16)  # ipLocation
    ws.set_column(8, 8, 18)  # author_nickname
    ws.set_column(9, 13, 14)  # counts
    ws.set_column(14, 14, 60)  # link
    ws.set_column(15, 15, 40)  # error

    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(1, len(rows)), len(headers) - 1)

    # Sheet2: summary
    ws2 = wb.add_worksheet("summary")
    ws2.write(0, 0, "generated_at", fmt_head)
    ws2.write(0, 1, datetime.now().isoformat(timespec="seconds"), fmt_cell)

    rowi = 2
    summary_items = [
        ("executed_keywords", summary.get("executed_keywords", 0)),
        ("successful_keywords", summary.get("successful_keywords", 0)),
        ("failed_keywords", summary.get("failed_keywords", 0)),
        ("total_details", summary.get("total_details", 0)),
        ("days", summary.get("days", 0)),
        ("candidate_per_keyword", summary.get("candidate_per_keyword", 0)),
        ("max_per_keyword", summary.get("max_per_keyword", 0)),
        ("max_total", summary.get("max_total", 0)),
    ]
    for k, v in summary_items:
        ws2.write(rowi, 0, k, fmt_head)
        ws2.write(rowi, 1, v, fmt_cell)
        rowi += 1

    # 失败原因列表
    rowi += 2
    ws2.write(rowi, 0, "失败原因", fmt_head)
    rowi += 1
    failed_details = summary.get("failed_details", [])
    for fd in failed_details:
        ws2.write(rowi, 0, fd.get("keyword"), fmt_cell)
        ws2.write(rowi, 1, fd.get("reason"), fmt_error)
        rowi += 1

    # 每关键词状态
    rowi += 2
    ws2.write(rowi, 0, "keyword", fmt_head)
    ws2.write(rowi, 1, "status", fmt_head)
    ws2.write(rowi, 2, "count", fmt_head)
    ws2.write(rowi, 3, "attempted", fmt_head)
    ws2.write(rowi, 4, "reason", fmt_head)
    rowi += 1
    for kw, info in per_keyword.items():
        ws2.write(rowi, 0, kw, fmt_cell)
        ws2.write(rowi, 1, info.get("status", "unknown"), fmt_cell)
        ws2.write(rowi, 2, info.get("count", ""), fmt_cell)
        ws2.write(rowi, 3, info.get("attempted", ""), fmt_cell)
        ws2.write(rowi, 4, info.get("reason", ""), fmt_cell)
        rowi += 1

    ws2.set_column(0, 0, 25)
    ws2.set_column(1, 1, 12)
    ws2.set_column(2, 3, 10)
    ws2.set_column(4, 4, 60)

    wb.close()


def _deterministic_sleep(idx: int, min_s: float, max_s: float) -> None:
    """确定性 sleep（不使用 random 模块）。"""
    span = max(0.0, max_s - min_s)
    # 使用 idx 产生伪随机但可重复的偏移
    offset = span * ((idx % 5) / 4.0)
    sleep_s = min_s + offset
    time.sleep(sleep_s)


def _is_within_last_days(unix_ts: int, days: int) -> bool:
    """检查时间戳是否在最近 N 天内（按北京时间计算）。

    unix_ts 支持秒/毫秒级。
    """
    if not unix_ts:
        return False
    if unix_ts >= 1_000_000_000_000:
        unix_ts //= 1000
    try:
        dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc).astimezone(ZoneInfo("Asia/Shanghai"))
        now = datetime.now(tz=ZoneInfo("Asia/Shanghai"))
        delta = now - dt
        return 0 <= delta.total_seconds() <= days * 86400
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="xhs detail export")
    ap.add_argument("--keywords-file", required=True, help="关键词文件路径")
    ap.add_argument("--host", default="127.0.0.1", help="CDP host")
    ap.add_argument("--port", type=int, default=9222, help="CDP port")
    ap.add_argument("--sort-by", default="综合", help="排序方式")
    ap.add_argument("--publish-time", default="一周内", help="发布时间范围")
    ap.add_argument("--days", type=int, default=7, help="仅保留最近 N 天（强校验，基于详情页 time）")
    ap.add_argument("--candidate-per-keyword", type=int, default=10, help="每关键词搜索候选池大小")
    ap.add_argument("--max-per-keyword", type=int, default=3, help="每关键词最多导出详情条数")
    ap.add_argument("--max-total", type=int, default=30, help="总详情条数上限")

    ap.add_argument("--sleep-keyword-min", type=float, default=2.0, help="keyword 间最小 sleep")
    ap.add_argument("--sleep-keyword-max", type=float, default=4.0, help="keyword 间最大 sleep")
    ap.add_argument("--sleep-detail-min", type=float, default=15.0, help="detail 后最小 sleep")
    ap.add_argument("--sleep-detail-max", type=float, default=25.0, help="detail 后最大 sleep")

    ap.add_argument("--out-json", required=True, help="输出 JSON 路径")
    ap.add_argument("--out-xlsx", required=True, help="输出 Excel 路径")

    args = ap.parse_args()

    keywords = _read_keywords(args.keywords_file)
    print(f"加载关键词：{len(keywords)} 个")

    rows: list[DetailRow] = []
    per_keyword: dict[str, dict[str, Any]] = {}
    failed_details: list[dict[str, str]] = []
    consecutive_fail = 0
    seen_links: set[str] = set()

    for idx, kw in enumerate(keywords, start=1):
        print(f"\n[{idx}/{len(keywords)}] 处理关键词：{kw}")

        # 全局总量限制
        if len(rows) >= args.max_total:
            print("  已达到 max_total，提前结束")
            break

        got_for_kw = 0
        kw_attempted = 0
        kw_fail_reason = ""

        try:
            # Step 1: search-feeds (候选池)
            feeds = _run_search(
                kw,
                host=args.host,
                port=args.port,
                sort_by=args.sort_by,
                publish_time=args.publish_time,
            )
            print(f"  搜索结果：{len(feeds)} 条")

            if not feeds:
                raise RuntimeError("搜索结果为空")

            # 限制候选池大小
            candidates = feeds[: max(1, args.candidate_per_keyword)]

            for i, feed in enumerate(candidates, start=1):
                if got_for_kw >= args.max_per_keyword or len(rows) >= args.max_total:
                    break

                feed_id = feed.get("id") or (feed.get("noteCard") or {}).get("id") or ""
                xsec_token = feed.get("xsecToken") or feed.get("xsec_token") or ""
                if not feed_id or not xsec_token:
                    continue

                link = f"https://www.xiaohongshu.com/explore/{feed_id}?xsec_token={xsec_token}"
                if link in seen_links:
                    continue
                seen_links.add(link)

                kw_attempted += 1
                print(f"  候选#{i}: feed_id={feed_id}")

                # Step 2: get-feed-detail
                try:
                    detail_data = _run_detail(feed_id, xsec_token, host=args.host, port=args.port)
                except Exception as e:
                    # 详情命令失败：记录但不中断关键词循环（不重试同链接）
                    kw_fail_reason = str(e)
                    failed_details.append({"keyword": kw, "feed_id": feed_id, "reason": kw_fail_reason})
                    _deterministic_sleep(idx + i, args.sleep_detail_min, args.sleep_detail_max)
                    continue

                # 检查错误（扫码/不可访问等）
                error_msg = _check_error(detail_data)
                if error_msg:
                    kw_fail_reason = error_msg
                    failed_details.append({"keyword": kw, "feed_id": feed_id, "reason": error_msg})
                    _deterministic_sleep(idx + i, args.sleep_detail_min, args.sleep_detail_max)
                    continue

                # 强校验：最近 N 天
                note = (detail_data.get("note") or {})
                tval = int(note.get("time") or 0)
                if not _is_within_last_days(tval, args.days):
                    # 不在时间窗口：跳过（不算脚本失败）
                    _deterministic_sleep(idx + i, args.sleep_detail_min, args.sleep_detail_max)
                    continue

                detail_row = _extract_detail_from_result(detail_data, kw)
                rows.append(detail_row)
                got_for_kw += 1

                # detail 后额外 sleep（防风控）
                _deterministic_sleep(idx + i, args.sleep_detail_min, args.sleep_detail_max)

            if got_for_kw > 0:
                per_keyword[kw] = {
                    "status": "success",
                    "count": got_for_kw,
                    "attempted": kw_attempted,
                }
                consecutive_fail = 0
            else:
                # 本关键词未拿到任何“最近N天”详情
                reason = kw_fail_reason or f"候选池内无最近{args.days}天的可用详情"
                per_keyword[kw] = {
                    "status": "failed",
                    "count": 0,
                    "attempted": kw_attempted,
                    "reason": reason,
                }
                consecutive_fail += 1
                if consecutive_fail >= 3:
                    print("  连续 3 个关键词无有效详情，终止任务")
                    break

        except Exception as e:
            error_str = str(e)
            print(f"  失败：{error_str}")
            failed_details.append({"keyword": kw, "reason": error_str})
            per_keyword[kw] = {"status": "failed", "count": 0, "attempted": kw_attempted, "reason": error_str}
            consecutive_fail += 1
            if consecutive_fail >= 3:
                print("  连续 3 个关键词失败，终止任务")
                break

        # keyword 间 sleep
        if idx < len(keywords):
            _deterministic_sleep(idx, args.sleep_keyword_min, args.sleep_keyword_max)

    # 构建汇总
    summary = {
        "executed_keywords": len(per_keyword),
        "successful_keywords": sum(1 for v in per_keyword.values() if v.get("status") == "success"),
        "failed_keywords": sum(1 for v in per_keyword.values() if v.get("status") == "failed"),
        "total_details": len(rows),
        "failed_details": failed_details,
        "days": args.days,
        "candidate_per_keyword": args.candidate_per_keyword,
        "max_per_keyword": args.max_per_keyword,
        "max_total": args.max_total,
    }

    # 写入 JSON
    payload = {
        "details": [
            {
                "keyword": r.keyword,
                "noteId": r.noteId,
                "title": r.title,
                "desc": r.desc,
                "type": r.type,
                "time": r.time,
                "time_beijing": r.time_beijing,
                "ipLocation": r.ipLocation,
                "author_nickname": r.author_nickname,
                "likedCount": r.likedCount,
                "collectedCount": r.collectedCount,
                "commentCount": r.commentCount,
                "sharedCount": r.sharedCount,
                "imageCount": r.imageCount,
                "link": r.link,
                "error": r.error,
            }
            for r in rows
        ],
        "summary": summary,
    }
    _write_json(args.out_json, payload)
    print(f"\nJSON 输出：{args.out_json}")

    # 写入 Excel
    _write_xlsx(args.out_xlsx, rows, summary, per_keyword)
    print(f"Excel 输出：{args.out_xlsx}")

    # 打印汇总
    print(f"\n=== 任务汇总 ===")
    print(f"执行关键词：{summary['executed_keywords']}")
    print(f"成功：{summary['successful_keywords']}")
    print(f"失败：{summary['failed_keywords']}")
    print(f"总详情数：{summary['total_details']}")

    if failed_details:
        print(f"\n失败详情:")
        for fd in failed_details:
            print(f"  - {fd.get('keyword')}: {fd.get('reason')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
