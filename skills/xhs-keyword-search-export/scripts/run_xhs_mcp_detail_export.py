#!/usr/bin/env python3
"""xhs MCP detail export: search_feeds -> get_feed_detail -> filter last N days -> Excel/JSON

适用场景
- 已通过 Agent Reach / Docker 启动 xiaohongshu-mcp，并在 mcporter 中配置了 server：xiaohongshu
- 需要“综合 + 最近一周”等筛选后，再用详情页 time 强校验（自然最近 N 天）
- 需要导出 Excel，且 desc 正文需要全量

依赖
- mcporter (npm -g mcporter)
- 已配置：mcporter config add xiaohongshu http://localhost:18060/mcp
- xiaohongshu-mcp 容器运行中且已登录

频控（默认更保守，可调）
- 每次 get_feed_detail 之间 sleep 3~6 秒随机
- 每个关键词连续拉取 4 次后额外 sleep 10~20 秒随机

输出
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
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
import re

from xhs_mcp_runtime import cleanup_xhs_mcp, ensure_xhs_mcp, runtime_summary


VENV_DIR = Path.home() / ".agent-reach" / "tools" / "xhs-keyword-search-export" / "venv"


def _ensure_xlsxwriter() -> None:
    """确保 xlsxwriter 可用。

    macOS 上系统 Python 可能启用了 PEP 668，直接 pip install 会失败。
    这里采用“自建 venv + 安装依赖 + 重新执行脚本”的方式，避免污染系统环境。
    """
    try:
        import xlsxwriter  # noqa: F401
        return
    except Exception:
        pass

    vpy = VENV_DIR / "bin" / "python"
    if not vpy.exists():
        VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)

    # install deps
    subprocess.run([str(vpy), "-m", "pip", "install", "-U", "pip", "wheel"], check=False)
    subprocess.run([str(vpy), "-m", "pip", "install", "xlsxwriter"], check=True)

    # re-exec within venv
    os.execv(str(vpy), [str(vpy), *sys.argv])


@dataclass
class Row:
    keyword: str
    note_id: str
    xsec_token: str
    title: str
    author_nickname: str
    publish_time: str  # Beijing string
    publish_ts: int
    note_type: str  # normal/video/etc
    image_urls: str  # newline-separated
    like_count: str
    comment_count: str
    collect_count: str
    url: str
    desc_full: str
    fetched_at: str
    # negative filter fields (optional)
    neg_flag: bool = False
    neg_score: int = 0
    neg_labels: str = ""  # comma-separated
    neg_reasons: str = ""  # comma-separated
    error: str = ""


def _read_keywords(path: str) -> list[str]:
    kws: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        kws.append(s)
    return kws


def _run(cmd: list[str], *, timeout: int = 90) -> str:
    # 确保使用正确的 mcporter 配置文件路径
    script_dir = Path(__file__).resolve().parent  # scripts/
    skill_dir = script_dir.parent  # xhs-keyword-search-export/
    skills_dir = skill_dir.parent  # skills/
    workspace_dir = skills_dir.parent  # .openclaw/workspace/
    config_path = workspace_dir / "config" / "mcporter.json"
    # 在 mcporter call 命令中插入 --config 参数
    if len(cmd) >= 2 and cmd[0] == "mcporter" and cmd[1] == "call":
        cmd.insert(1, "--config")
        cmd.insert(2, str(config_path))
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "unknown error").strip())
    return p.stdout


def _mcporter_call(selector: str, *, timeout_ms: int = 120000, retries: int = 1, retry_sleep: float = 8.0) -> Any:
    """Call mcporter tool with --args JSON format.
    
    Supports:
    - xiaohongshu.search_feeds(keyword: 'xxx', filters: {...}) -> {"keyword": "xxx"}
    - xiaohongshu.get_feed_detail(feed_id: 'xxx', xsec_token: 'yyy') -> {"feed_id": "xxx", "xsec_token": "yyy"}
    
    timeout_ms: mcporter call timeout
    retries: number of retry attempts for transient errors
    retry_sleep: seconds between retries
    """
    # Try to parse search_feeds first
    search_match = re.search(r'''search_feeds\(keyword:\s*(['"])([^'"]+)\1''', selector)
    if search_match:
        keyword = search_match.group(2)
        args_json = json.dumps({"keyword": keyword})
        tool_name = "xiaohongshu.search_feeds"
    else:
        # Try get_feed_detail
        detail_match = re.search(r'''get_feed_detail\(feed_id:\s*(['"])([^'"]+)\1,\s*xsec_token:\s*(['"])([^'"]+)\3\)''', selector)
        if not detail_match:
            raise RuntimeError(f"无法解析 selector: {selector}")
        feed_id = detail_match.group(2)
        xsec_token = detail_match.group(4)
        args_json = json.dumps({"feed_id": feed_id, "xsec_token": xsec_token})
        tool_name = "xiaohongshu.get_feed_detail"
    
    # Calculate config path: scripts -> skill -> skills -> workspace
    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    skills_dir = skill_dir.parent
    workspace_dir = skills_dir.parent
    config_path = workspace_dir / "config" / "mcporter.json"
    
    last_err = ""
    for attempt in range(retries + 1):
        cmd = ["mcporter", "--config", str(config_path), "call", tool_name, "--args", args_json, "--output", "json", "--timeout", str(timeout_ms)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=max(60, timeout_ms // 1000 + 30))
        out = (p.stdout or "").strip()
        err = (p.stderr or "").strip()
        
        if out:
            try:
                return json.loads(out)
            except Exception:
                last_err = f"mcporter output not json: {out[:200]}, stderr: {err[:500]}"
        else:
            last_err = f"empty output, stderr: {err[:500]}"
        
        # Check for transient errors
        transient = any(k in last_err.lower() for k in ["timed out", "timeout", "offline", "connection refused", "bad gateway"])
        if attempt < retries and transient:
            time.sleep(retry_sleep)
            continue
        
        # For non-transient errors (like note not accessible), don't retry
        if "不可访问" in last_err or "not available" in last_err.lower():
            raise RuntimeError(last_err[:500])
            
        raise RuntimeError(last_err)
    
    raise RuntimeError(last_err or "mcporter call failed")


def _now_bj() -> datetime:
    return datetime.now(tz=ZoneInfo("Asia/Shanghai"))


def _format_bj(ts_ms: int) -> str:
    if not ts_ms:
        return ""
    ts = ts_ms
    if ts >= 1_000_000_000_000:
        ts //= 1000
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(ZoneInfo("Asia/Shanghai"))
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _within_last_days(ts_ms: int, days: int) -> bool:
    if not ts_ms:
        return False
    ts = ts_ms
    if ts >= 1_000_000_000_000:
        ts //= 1000
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(ZoneInfo("Asia/Shanghai"))
    delta = _now_bj() - dt
    return 0 <= delta.total_seconds() <= days * 86400


_NEXT_ALLOWED_TS: float = 0.0


def _sleep_seconds(idx: int, min_s: float, max_s: float) -> None:
    """全局速率限制器 + 抖动 sleep。

    - 全局：保证任意两次网络调用之间至少间隔 min_s~max_s（带抖动）
    - 通过 idx + 当前秒做轻量伪随机，避免引入 random
    """
    global _NEXT_ALLOWED_TS

    span = max(0.0, max_s - min_s)
    seed = int(time.time()) + idx * 97
    frac = (seed % 1000) / 1000.0
    target_sleep = min_s + span * frac

    now = time.time()
    if _NEXT_ALLOWED_TS > now:
        time.sleep(_NEXT_ALLOWED_TS - now)

    time.sleep(target_sleep)
    _NEXT_ALLOWED_TS = time.time()

def _extract_from_detail(detail: dict[str, Any], *, keyword: str, feed_id: str, xsec_token: str) -> Row:
    # detail shape: { feed_id, data: { note: {...}, comments: {...} } }
    data = detail.get("data") or {}
    note = data.get("note") or {}
    user = note.get("user") or {}
    interact = note.get("interactInfo") or {}

    title = str(note.get("title") or "")
    desc = str(note.get("desc") or "")
    ts = int(note.get("time") or 0)
    note_type = str(note.get("type") or "")

    nickname = str(user.get("nickname") or user.get("nickName") or "")

    like_count = str(interact.get("likedCount") or "")
    comment_count = str(interact.get("commentCount") or "")
    collect_count = str(interact.get("collectedCount") or "")

    # images
    image_list = note.get("imageList") or []
    urls: list[str] = []
    if isinstance(image_list, list):
        for im in image_list:
            if not isinstance(im, dict):
                continue
            u = im.get("urlDefault") or im.get("urlPre") or ""
            if u:
                urls.append(str(u))
    image_urls = "\n".join(urls)

    url = f"https://www.xiaohongshu.com/explore/{feed_id}?xsec_token={xsec_token}" if xsec_token else f"https://www.xiaohongshu.com/explore/{feed_id}"

    return Row(
        keyword=keyword,
        note_id=feed_id,
        xsec_token=xsec_token,
        title=title,
        author_nickname=nickname,
        publish_time=_format_bj(ts),
        publish_ts=ts,
        note_type=note_type,
        image_urls=image_urls,
        like_count=like_count,
        comment_count=comment_count,
        collect_count=collect_count,
        url=url,
        desc_full=desc,
        fetched_at=_now_bj().isoformat(timespec="seconds"),
    )


def _write_json(path: str, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_lexicon(path: str) -> dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def _contains_any(text: str, terms: list[str]) -> list[str]:
    hits: list[str] = []
    for t in terms:
        if t and t in text:
            hits.append(t)
    return hits


def _label_hits(text: str, signals: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    labels: list[str] = []
    reasons: list[str] = []

    mapping = {
        "uninstall_close": "卸载/关闭困难",
        "bug": "异常/bug",
        "performance": "体验问题",
        "ads": "广告/打扰",
    }

    for key, terms in signals.items():
        hits = _contains_any(text, terms)
        if not hits:
            continue
        reasons.extend(hits)
        label = mapping.get(key)
        if label and label not in labels:
            labels.append(label)

    return labels, reasons


def _match_strong_patterns(text: str, patterns: list[str]) -> list[str]:
    hits: list[str] = []
    for pat in patterns:
        if not pat:
            continue
        try:
            if re.search(pat, text):
                hits.append(pat)
        except re.error:
            # ignore invalid patterns
            continue
    return hits


def _neg_classify(text: str, lex: dict[str, Any]) -> tuple[bool, int, list[str], list[str]]:
    """Return (neg_flag, score, labels, reasons). High-recall rule-based."""
    exclude = lex.get("exclude") or []
    signals = lex.get("signals") or {}
    strong_patterns = lex.get("strong_patterns") or []
    tone = lex.get("tone") or []

    # hard exclude for obvious tutorials/marketing
    if _contains_any(text, exclude):
        return False, 0, [], []

    labels, reasons = _label_hits(text, signals)

    score = len(set(reasons))

    strong_hits = _match_strong_patterns(text, strong_patterns)
    if strong_hits:
        score += 3
        reasons.extend([f"re:{h}" for h in strong_hits])

    tone_hits = _contains_any(text, tone)
    if tone_hits:
        score += 1
        reasons.extend(tone_hits)

    neg_flag = (score >= 2) or bool(strong_hits)
    return neg_flag, score, labels, sorted(set(reasons))


def _write_xlsx(path: str, rows: list[Row], summary: dict[str, Any], per_keyword: dict[str, Any]) -> None:
    # ensure dependency (may re-exec the script)
    _ensure_xlsxwriter()
    import xlsxwriter  # type: ignore

    Path(path).parent.mkdir(parents=True, exist_ok=True)

    wb = xlsxwriter.Workbook(path)
    fmt_head = wb.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1, "text_wrap": True})
    fmt_cell = wb.add_format({"text_wrap": True, "valign": "top", "border": 1})
    fmt_link = wb.add_format({"color": "#0563C1", "underline": 1, "valign": "top", "border": 1})
    fmt_error = wb.add_format({"text_wrap": True, "valign": "top", "border": 1, "font_color": "red"})

    # details
    ws = wb.add_worksheet("details")
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
    ]
    for c, h in enumerate(headers):
        ws.write(0, c, h, fmt_head)

    for r, row in enumerate(rows, start=1):
        ws.write(r, 0, row.keyword, fmt_cell)
        ws.write(r, 1, row.note_id, fmt_cell)
        ws.write(r, 2, row.xsec_token, fmt_cell)
        ws.write(r, 3, row.title, fmt_cell)
        ws.write(r, 4, row.author_nickname, fmt_cell)
        ws.write(r, 5, row.publish_time, fmt_cell)
        ws.write(r, 6, row.publish_ts, fmt_cell)
        ws.write(r, 7, row.note_type, fmt_cell)
        ws.write(r, 8, row.image_urls, fmt_cell)
        ws.write(r, 9, row.like_count, fmt_cell)
        ws.write(r, 10, row.comment_count, fmt_cell)
        ws.write(r, 11, row.collect_count, fmt_cell)
        if row.url:
            ws.write_url(r, 12, row.url, fmt_link, string=row.url)
        else:
            ws.write(r, 12, "", fmt_cell)
        ws.write(r, 13, row.desc_full, fmt_cell)
        ws.write(r, 14, row.fetched_at, fmt_cell)
        ws.write(r, 15, "TRUE" if row.neg_flag else "FALSE", fmt_cell)
        ws.write(r, 16, row.neg_score, fmt_cell)
        ws.write(r, 17, row.neg_labels, fmt_cell)
        ws.write(r, 18, row.neg_reasons, fmt_cell)
        if row.error:
            ws.write(r, 19, row.error, fmt_error)
        else:
            ws.write(r, 19, "", fmt_cell)

    ws.set_column(0, 0, 18)
    ws.set_column(1, 2, 26)
    ws.set_column(3, 3, 40)
    ws.set_column(4, 6, 18)
    ws.set_column(7, 7, 12)
    ws.set_column(8, 8, 60)
    ws.set_column(9, 11, 14)
    ws.set_column(12, 12, 60)
    ws.set_column(13, 13, 80)
    ws.set_column(14, 14, 20)
    ws.set_column(15, 16, 10)
    ws.set_column(17, 17, 22)
    ws.set_column(18, 18, 50)
    ws.set_column(19, 19, 30)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(1, len(rows)), len(headers) - 1)

    # summary
    ws2 = wb.add_worksheet("summary")
    ws2.write(0, 0, "generated_at", fmt_head)
    ws2.write(0, 1, _now_bj().isoformat(timespec="seconds"), fmt_cell)

    rowi = 2
    for k, v in summary.items():
        if k in ("failed_details",):
            continue
        ws2.write(rowi, 0, k, fmt_head)
        ws2.write(rowi, 1, str(v), fmt_cell)
        rowi += 1

    rowi += 2
    ws2.write(rowi, 0, "failed_details", fmt_head)
    rowi += 1
    for fd in summary.get("failed_details", []):
        ws2.write(rowi, 0, fd.get("keyword", ""), fmt_cell)
        ws2.write(rowi, 1, fd.get("feed_id", ""), fmt_cell)
        ws2.write(rowi, 2, fd.get("reason", ""), fmt_error)
        rowi += 1

    rowi += 2
    ws2.write(rowi, 0, "keyword", fmt_head)
    ws2.write(rowi, 1, "status", fmt_head)
    ws2.write(rowi, 2, "count", fmt_head)
    ws2.write(rowi, 3, "attempted", fmt_head)
    ws2.write(rowi, 4, "reason", fmt_head)
    rowi += 1
    for kw, info in per_keyword.items():
        ws2.write(rowi, 0, kw, fmt_cell)
        ws2.write(rowi, 1, info.get("status", ""), fmt_cell)
        ws2.write(rowi, 2, info.get("count", ""), fmt_cell)
        ws2.write(rowi, 3, info.get("attempted", ""), fmt_cell)
        ws2.write(rowi, 4, info.get("reason", ""), fmt_cell)
        rowi += 1

    ws2.set_column(0, 0, 28)
    ws2.set_column(1, 3, 12)
    ws2.set_column(4, 4, 60)

    wb.close()


# ============================================================================
# IP 风控自动重试功能
# ============================================================================

def _check_mcp_ready() -> bool:
    """检查 MCP 服务是否就绪。"""
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:18060/mcp", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except:
        # 405 或其他错误也表示服务已启动
        return True


def _check_ip_risk() -> bool:
    """检查是否遇到 IP 风控。
    
    通过测试调用 get_feed_detail 检测是否返回"笔记不可访问"错误。
    返回 True 表示检测到 IP 风控。
    """
    test_feed_id = "67fba64a000000001d003885"
    test_xsec_token = "ABV_MdNbPkKk-ppHqki_vItXTdLDep8ocgGCIKWOAWpsA="
    
    try:
        # 计算配置文件路径
        script_dir = Path(__file__).resolve().parent
        workspace_dir = script_dir.parent.parent
        config_path = workspace_dir / "config" / "mcporter.json"
        
        args_json = json.dumps({"feed_id": test_feed_id, "xsec_token": test_xsec_token})
        cmd = ["mcporter", "--config", str(config_path), "call", "xiaohongshu.get_feed_detail", 
               "--args", args_json, "--output", "json", "--timeout", "30"]
        
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        out = (p.stdout or "").strip()
        
        # 检查是否返回错误
        if "不可访问" in out or "Not Available" in out or "isError" in out:
            return True
        
        # 尝试解析 JSON，看是否有正常数据
        try:
            data = json.loads(out)
            if "data" in data and "note" in data.get("data", {}):
                return False  # 正常返回
        except:
            pass
        
        return False
    except Exception:
        return False


def _restart_xhs_mcp_container() -> bool:
    """重启 xiaohongshu-mcp 容器以刷新 IP 状态。
    
    返回 True 表示重启成功。
    """
    print("\n🔄 检测到 IP 风控，尝试重启 MCP 容器刷新 IP...")
    
    try:
        # 停止容器
        subprocess.run(["docker", "stop", "xiaohongshu-mcp"], 
                      capture_output=True, text=True, timeout=30)
        print("  ⏹️  容器已停止")
        
        # 等待 2 秒
        time.sleep(2)
        
        # 启动容器
        subprocess.run(["docker", "start", "xiaohongshu-mcp"], 
                      capture_output=True, text=True, timeout=30)
        print("  ▶️  容器已启动")
        
        # 等待服务就绪（通常 5-10 秒）
        print("  ⏳  等待 MCP 服务就绪...")
        for i in range(15):
            time.sleep(1)
            if _check_mcp_ready():
                print("  ✅ MCP 服务已就绪")
                return True
        
        print("  ⚠️  等待超时，但继续尝试执行")
        return True
    except Exception as e:
        print(f"  ❌ 重启失败：{e}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="xhs MCP detail export")
    ap.add_argument("--keywords-file", required=True)
    ap.add_argument("--limit-keywords", type=int, default=0, help="仅取前 N 个关键词（0 表示不限制）")
    ap.add_argument("--days", type=int, default=0, help="强校验：仅保留最近 N 天（0 表示不做时间强校验；默认禁用）")
    ap.add_argument("--sort-by", default="综合", help="排序方式：综合/最新/最热/最多点赞（默认综合）")
    ap.add_argument("--publish-time", default="一周内", help="搜索筛选发布时间（如 一周内/一天内 等；默认一周内）")

    ap.add_argument("--candidate-per-keyword", type=int, default=10)
    ap.add_argument("--need-per-keyword", type=int, default=2, help="每个关键词需要补齐的条数")
    ap.add_argument("--max-total", type=int, default=30)

    ap.add_argument("--sleep-detail-min", type=float, default=3.0)
    ap.add_argument("--sleep-detail-max", type=float, default=6.0)
    ap.add_argument("--sleep-burst-every", type=int, default=4)
    ap.add_argument("--sleep-burst-min", type=float, default=10.0)
    ap.add_argument("--sleep-burst-max", type=float, default=20.0)

    # negative filter (high recall) - 默认启用
    ap.add_argument("--negative-only", action="store_true", default=True, help="只保留负面内容（四类），并补齐到 need-per-keyword（默认启用）")
    ap.add_argument("--no-negative-filter", action="store_false", dest="negative_only", help="关闭负面过滤（默认开启）")
    ap.add_argument(
        "--negative-lexicon",
        default=str(Path(__file__).resolve().parent.parent / "references" / "negative_lexicon.json"),
        help="负面词典/模式 JSON 路径",
    )
    ap.add_argument("--max-detail-per-keyword", type=int, default=20, help="每关键词最多拉取详情条数（风控上限）")

    ap.add_argument("--search-timeout-ms", type=int, default=90000, help="search_feeds 的 mcporter 超时（毫秒）")
    ap.add_argument("--search-retry", type=int, default=1, help="search_feeds 超时/离线时重试次数（默认1）")
    ap.add_argument("--search-retry-sleep", type=float, default=15.0, help="search_feeds 重试前等待秒数（默认15s）")

    ap.add_argument("--auto-retry-ip-risk", action="store_true", default=True,
                   help="遇到 IP 风控时自动重启容器并重试（默认启用）")
    ap.add_argument("--max-ip-retry", type=int, default=1, help="IP 风控自动重试次数（默认 1 次）")

    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-xlsx", required=True)

    args = ap.parse_args()

    try:
        ensure_xhs_mcp()
        print(f"[runtime] {runtime_summary()}")

        # IP 风控自动检测和重试（最多重试 N 次）
        ip_retry_count = 0
        max_ip_retry = getattr(args, 'max_ip_retry', 1)
        auto_retry = getattr(args, 'auto_retry_ip_risk', True)
        
        while ip_retry_count <= max_ip_retry:
            if ip_retry_count > 0:
                print(f"\n🔄 IP 风控重试 #{ip_retry_count}/{max_ip_retry}")
            
            # 检查是否遇到 IP 风控
            if auto_retry and _check_ip_risk():
                print("\n⚠️  检测到 IP 风控限制")
                if ip_retry_count < max_ip_retry:
                    if _restart_xhs_mcp_container():
                        ip_retry_count += 1
                        print(f"✅ 容器已重启，等待 10 秒后重试...\n")
                        time.sleep(10)
                        continue
                else:
                    print("❌ 已达最大重试次数，继续执行（可能失败）\n")
            break

        keywords = _read_keywords(args.keywords_file)
        if args.limit_keywords and args.limit_keywords > 0:
            keywords = keywords[: args.limit_keywords]
        rows: list[Row] = []
        per_keyword: dict[str, dict[str, Any]] = {}
        failed_details: list[dict[str, str]] = []

        seen: set[str] = set()
        lex: dict[str, Any] | None = None

        total_keywords = len(keywords)

        for kidx, kw in enumerate(keywords, start=1):
            if len(rows) >= args.max_total:
                break

            got = 0
            attempted = 0
            reason = ""
            skipped_bad_id = 0
            details_fetched = 0

            try:
                # build filters: publish_time optional
                if args.publish_time:
                    selector = (
                        f"xiaohongshu.search_feeds(keyword: {kw!r}, "
                        f"filters: {{sort_by: {args.sort_by!r}, publish_time: {args.publish_time!r}}})"
                    )
                else:
                    selector = (
                        f"xiaohongshu.search_feeds(keyword: {kw!r}, "
                        f"filters: {{sort_by: {args.sort_by!r}}})"
                    )

                # search_feeds: distinguish true-empty vs transient timeout/offline; retry once (configurable)
                search = None
                last_err = ""
                for attempt in range(args.search_retry + 1):
                    try:
                        search = _mcporter_call(
                            selector,
                            timeout_ms=args.search_timeout_ms,
                            retries=args.search_retry,
                            retry_sleep=args.search_retry_sleep,
                        )
                        break
                    except Exception as e:
                        last_err = str(e)
                        msg = last_err.lower()
                        transient = (
                            "timed out" in msg
                            or "timeout" in msg
                            or "offline" in msg
                            or "appears offline" in msg
                        )
                        if attempt < args.search_retry and transient:
                            time.sleep(args.search_retry_sleep)
                            continue
                        raise

                feeds = (search or {}).get("feeds") or []
                if not isinstance(feeds, list):
                    feeds = []
                if not feeds:
                    # true empty result; not an error
                    per_keyword[kw] = {"status": "empty", "count": 0, "attempted": 0, "reason": "搜索结果为空"}
                    continue

                candidates = feeds[: max(1, args.candidate_per_keyword)]
                total_candidates = len(candidates)
                progress_interval = max(1, total_candidates // 4)  # 每 25% 播报一次

                print(f"[{kidx}/{total_keywords}] 开始处理关键词：{kw} (候选{total_candidates}条，目标{args.need_per_keyword}条)")

                burst_count = 0
                for cand_idx, feed in enumerate(candidates, start=1):
                    if got >= args.need_per_keyword or len(rows) >= args.max_total:
                        break
                    if details_fetched >= args.max_detail_per_keyword:
                        break

                    feed_id = str(feed.get("id") or "")
                    xsec_token = str(feed.get("xsecToken") or "")
                    if not feed_id or not xsec_token:
                        continue

                    # filter out non-note ids (e.g., uuid#timestamp)
                    if ("#" in feed_id) or ("-" in feed_id) or (not re.fullmatch(r"[0-9a-f]{24}", feed_id)):
                        skipped_bad_id += 1
                        continue

                    uniq = f"{feed_id}|{xsec_token}"
                    if uniq in seen:
                        continue
                    seen.add(uniq)

                    attempted += 1

                    # 进度播报：每 N 条或关键节点
                    if cand_idx % progress_interval == 0 or cand_idx == 1 or cand_idx == total_candidates:
                        print(f"  [{kw}] 详情抓取进度：{cand_idx}/{total_candidates} (已获取{got}条，已拉详情{details_fetched}条)")

                    try:
                        detail = _mcporter_call(
                            f"xiaohongshu.get_feed_detail(feed_id: {feed_id!r}, xsec_token: {xsec_token!r})",
                            timeout_ms=120000,
                            retries=1,
                            retry_sleep=8.0,
                        )
                        details_fetched += 1
                    except Exception as e:
                        reason = str(e)
                        failed_details.append({"keyword": kw, "feed_id": feed_id, "reason": reason})
                        print(f"  [{kw}] 详情抓取失败：{feed_id[:12]}... - {reason[:80]}")
                        _sleep_seconds(kidx * 100 + attempted, args.sleep_detail_min, args.sleep_detail_max)
                        continue

                    # time window filter (strong check) - optional
                    if args.days and args.days > 0:
                        ts = int(((detail.get("data") or {}).get("note") or {}).get("time") or 0)
                        if not _within_last_days(ts, args.days):
                            _sleep_seconds(kidx * 100 + attempted, args.sleep_detail_min, args.sleep_detail_max)
                            continue

                    row = _extract_from_detail(detail, keyword=kw, feed_id=feed_id, xsec_token=xsec_token)

                    # negative-only filter (high recall)
                    if args.negative_only:
                        if lex is None:
                            lex = _load_lexicon(args.negative_lexicon)
                        text = (row.title or "") + "\n" + (row.desc_full or "")
                        neg_flag, neg_score, labels, reasons2 = _neg_classify(text, lex)
                        row.neg_flag = bool(neg_flag)
                        row.neg_score = int(neg_score)
                        row.neg_labels = ",".join(labels)
                        row.neg_reasons = ",".join(reasons2)
                        if not row.neg_flag:
                            _sleep_seconds(kidx * 100 + attempted, args.sleep_detail_min, args.sleep_detail_max)
                            continue

                    rows.append(row)
                    got += 1

                    # 频控
                    burst_count += 1
                    _sleep_seconds(kidx * 100 + attempted, args.sleep_detail_min, args.sleep_detail_max)
                    if args.sleep_burst_every > 0 and burst_count % args.sleep_burst_every == 0:
                        _sleep_seconds(kidx * 1000 + burst_count, args.sleep_burst_min, args.sleep_burst_max)

                if got >= args.need_per_keyword:
                    per_keyword[kw] = {
                        "status": "success",
                        "count": got,
                        "attempted": attempted,
                        "details_fetched": details_fetched,
                        "skipped_bad_id": skipped_bad_id,
                    }
                else:
                    per_keyword[kw] = {
                        "status": "insufficient_negative" if args.negative_only else "failed",
                        "count": got,
                        "attempted": attempted,
                        "details_fetched": details_fetched,
                        "skipped_bad_id": skipped_bad_id,
                        "reason": reason or f"负面不足：在最多{args.max_detail_per_keyword}条详情验证内无法补齐到 {args.need_per_keyword} 条",
                    }

            except Exception as e:
                per_keyword[kw] = {
                    "status": "failed",
                    "count": got,
                    "attempted": attempted,
                    "details_fetched": details_fetched,
                    "skipped_bad_id": skipped_bad_id,
                    "reason": str(e),
                }

            # checkpoint: write partial JSON after each keyword
            try:
                summary_tmp = {
                    "executed_keywords": len(per_keyword),
                    "successful_keywords": sum(1 for v in per_keyword.values() if v.get("status") == "success"),
                    "failed_keywords": sum(1 for v in per_keyword.values() if v.get("status") == "failed"),
                    "empty_keywords": sum(1 for v in per_keyword.values() if v.get("status") == "empty"),
                    "insufficient_keywords": sum(1 for v in per_keyword.values() if v.get("status") == "insufficient_negative"),
                    "total_details": len(rows),
                }
                _write_json(args.out_json, {"details": [asdict(r) for r in rows], "per_keyword": per_keyword, "summary": summary_tmp})
            except Exception:
                pass

            # progress line (one per keyword)
            print(f"[{kidx}/{total_keywords}] {kw} -> kept={got} fetched={details_fetched} skipped_bad_id={skipped_bad_id} status={per_keyword[kw].get('status')}")

        summary = {
            "executed_keywords": len(per_keyword),
            "successful_keywords": sum(1 for v in per_keyword.values() if v.get("status") == "success"),
            "failed_keywords": sum(1 for v in per_keyword.values() if v.get("status") == "failed"),
            "empty_keywords": sum(1 for v in per_keyword.values() if v.get("status") == "empty"),
            "insufficient_keywords": sum(1 for v in per_keyword.values() if v.get("status") == "insufficient_negative"),
            "total_details": len(rows),
            "days_strong_check": args.days,
            "publish_time_filter": args.publish_time,
            "candidate_per_keyword": args.candidate_per_keyword,
            "need_per_keyword": args.need_per_keyword,
            "max_total": args.max_total,
            "failed_details": failed_details,
            "search": {
                "timeout_ms": args.search_timeout_ms,
                "retry": args.search_retry,
                "retry_sleep": args.search_retry_sleep,
            },
        }

        payload = {
            "details": [asdict(r) for r in rows],
            "summary": summary,
            "per_keyword": per_keyword,
            "negative_filter": {
                "enabled": bool(args.negative_only),
                "lexicon": args.negative_lexicon if args.negative_only else "",
                "threshold": 2,
                "max_detail_per_keyword": args.max_detail_per_keyword,
            },
        }

        _write_json(args.out_json, payload)
        _write_xlsx(args.out_xlsx, rows, summary, per_keyword)

        print(f"JSON 输出：{args.out_json}")
        print(f"Excel 输出：{args.out_xlsx}")
        return 0
    finally:
        cleanup_xhs_mcp()


if __name__ == "__main__":
    raise SystemExit(main())
