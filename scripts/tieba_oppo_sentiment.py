#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baidu Tieba public-opinion collector (MVP)

Strategy (works around Tieba anti-bot slider):
- Use Bing CN web search with `site:tieba.baidu.com` queries.
- Parse SERP titles/snippets/urls.
- Do lightweight rule-based relevance + classification.

Output:
- JSONL: out/tieba_oppo_daily_<YYYYMMDD>.jsonl
- CSV:   out/tieba_oppo_daily_<YYYYMMDD>.csv
- MD:    out/tieba_oppo_daily_<YYYYMMDD>.md

Notes:
- This is a TEST-PHASE collector; it relies on search snippets. It does not fetch Tieba pages.
"""

from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from typing import Iterable, List, Dict, Tuple


PLATFORM = "百度贴吧"
TOPIC = "OPPO 游戏助手"

CORE_TERMS = [
    "OPPO游戏助手",
    "OPPO 游戏助手",
    "一加游戏助手",
    "一加 游戏助手",
    "ColorOS 游戏助手",
    "游戏侧边栏",
    "OPPO 侧边栏",
    "一加 侧边栏",
    "电竞模式",
    "云加速",
    "旁路供电",
]

PROBLEM_TERMS = [
    "卡顿",
    "掉帧",
    "锁30帧",
    "只有60帧",
    "120帧",
    "发热",
    "失效",
    "没了",
    "消失",
    "调不出来",
    "划不动",
    "扫不出来",
    "不支持",
    "失灵",
    "广告",
    "封号",
    "异常",
    "bug",
    "问题",
    "关闭",
    "卸载",
    "更新后",
]

INTENT_TERMS = [
    "为什么",
    "怎么办",
    "求救",
    "求解决",
    "什么情况",
    "有人遇到吗",
    "避坑",
    "反馈",
    "建议",
    "希望增加",
    "怎么关闭",
    "怎么卸载",
]

EXCLUDE_TERMS = [
    "外挂",
    "脚本",
    "辅助器",
    "模拟器",
    "修改器",
    "代练",
]

GAMES = ["王者荣耀", "原神", "三角洲行动"]

CATEGORY_RULES: List[Tuple[str, List[str]]] = [
    ("功能异常", ["失效", "消失", "没了", "调不出来", "失灵", "不支持"]),
    ("性能帧率", ["卡顿", "掉帧", "锁30帧", "只有60帧", "120帧", "发热"]),
    ("更新回归", ["更新后", "更新", "回归"]),
    ("广告争议", ["广告"]),
    ("兼容识别", ["不支持", "识别", "扫不出来"]),
    ("风险封号", ["封号", "风险"]),
    ("关闭卸载", ["关闭", "卸载", "怎么关闭", "怎么卸载"]),
    ("用户建议", ["建议", "希望增加", "反馈"]),
]

NEGATIVE_HINTS = PROBLEM_TERMS + ["吐槽", "垃圾", "离谱", "烦", "坑", "难用", "崩溃", "无法", "不能"]
POSITIVE_HINTS = ["解决", "已解决", "搞定", "好用", "赞", "推荐"]


@dataclasses.dataclass
class Item:
    platform: str
    search_term: str
    tieba_name: str
    title: str
    summary: str
    publish_time: str
    url: str
    reply_count: str
    relevance: float
    keep: bool
    category: str
    sentiment: str
    severity: int
    hit_keywords: List[str]
    conclusion: str


def _http_get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    # Bing is utf-8
    return data.decode("utf-8", errors="replace")


def _strip_tags(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_bing_results(html_text: str) -> List[Dict[str, str]]:
    """Very lightweight parser for Bing SERP.

    Bing markup changes frequently; we parse by:
    - splitting on <li ... class="b_algo" ...>
    - extracting the first h2/a as title+url
    - extracting the first caption <p> as snippet
    """
    results: List[Dict[str, str]] = []

    pat = r"<li[^>]*class=\"b_algo\"[^>]*>"
    blocks = re.split(pat, html_text)

    for b in blocks[1:]:
        # Title + URL
        m = re.search(r"<h2[^>]*>\s*<a[^>]+href=\"([^\"]+)\"[^>]*>([\s\S]*?)</a>", b)
        if not m:
            continue
        url = html.unescape(m.group(1))
        title = _strip_tags(m.group(2))

        # Snippet (prefer b_caption)
        sm = re.search(r"class=\"b_caption\"[\s\S]*?<p>([\s\S]*?)</p>", b)
        snippet = _strip_tags(sm.group(1)) if sm else ""
        if not snippet:
            sm2 = re.search(r"<p>([\s\S]*?)</p>", b)
            snippet = _strip_tags(sm2.group(1)) if sm2 else ""

        results.append({"title": title, "snippet": snippet, "url": url})

    return results


def build_queries() -> List[str]:
    queries: List[str] = []

    # High precision core
    for core in ["OPPO 游戏助手", "一加 游戏助手", "ColorOS 游戏助手", "游戏侧边栏", "电竞模式", "云加速", "旁路供电"]:
        queries.append(f"site:tieba.baidu.com {core}")

    # Core/feature + problem
    for core in ["OPPO 游戏助手", "一加 游戏助手", "ColorOS 游戏助手", "游戏侧边栏", "电竞模式", "云加速", "旁路供电"]:
        for prob in ["卡顿", "掉帧", "失效", "消失", "调不出来", "广告", "封号", "卸载", "更新后"]:
            queries.append(f"site:tieba.baidu.com {core} {prob}")

    # Core/feature + game
    for core in ["OPPO 游戏助手", "游戏侧边栏", "电竞模式", "云加速", "旁路供电"]:
        for g in GAMES:
            queries.append(f"site:tieba.baidu.com {core} {g}")

    # Exclusion (reduce noise) - apply in filter stage, but add here too
    return queries


def normalize_url(u: str) -> str:
    # Strip bing redirect wrappers etc.
    # Keep tieba.baidu.com URLs as-is; otherwise keep.
    if "bing.com" in u and "r=" in u:
        try:
            parsed = urllib.parse.urlparse(u)
            qs = urllib.parse.parse_qs(parsed.query)
            if "r" in qs:
                return qs["r"][0]
        except Exception:
            pass
    return u


def compute_relevance(text: str) -> Tuple[float, List[str], bool]:
    hits: List[str] = []

    def hit_any(terms: Iterable[str]) -> int:
        c = 0
        for t in terms:
            if t and t in text:
                hits.append(t)
                c += 1
        return c

    # Exclusion
    if any(t in text for t in EXCLUDE_TERMS):
        return 0.0, hits, False

    core_hits = hit_any(CORE_TERMS)
    prob_hits = hit_any(PROBLEM_TERMS)
    intent_hits = hit_any(INTENT_TERMS)

    # Special: if only "游戏助手" but no OPPO/OnePlus/ColorOS/feature hints, downweight
    has_generic = "游戏助手" in text
    has_brand_or_feature = any(k in text for k in ["OPPO", "一加", "ColorOS", "侧边栏", "电竞模式", "云加速", "旁路供电"])

    score = 0.0
    score += min(core_hits, 3) * 1.6
    score += min(prob_hits, 3) * 1.2
    score += min(intent_hits, 2) * 0.6

    if has_generic and not has_brand_or_feature:
        score *= 0.35

    keep = score >= 2.2 and (core_hits > 0 or has_brand_or_feature) and prob_hits > 0
    # Allow keep if strong feature mention + problem
    if ("电竞模式" in text or "游戏侧边栏" in text or "旁路供电" in text or "云加速" in text) and prob_hits > 0:
        keep = score >= 1.8

    return round(score, 2), sorted(set(hits)), keep


def classify(text: str) -> str:
    for cat, kws in CATEGORY_RULES:
        if any(k in text for k in kws):
            return cat
    # Fallback
    if any(k in text for k in PROBLEM_TERMS):
        return "功能异常"
    return "用户建议"


def sentiment_and_severity(text: str) -> Tuple[str, int]:
    # sentiment
    s = "neutral"
    if any(k in text for k in POSITIVE_HINTS):
        s = "positive"
    if any(k in text for k in NEGATIVE_HINTS) or any(k in text for k in INTENT_TERMS):
        s = "negative"

    # severity (1-5)
    sev = 2
    strong = ["无法", "不能", "完全", "彻底", "失效", "封号", "崩溃", "严重", "更新后"]
    mid = ["卡顿", "掉帧", "发热", "异常", "bug", "广告", "消失", "调不出来"]

    if any(k in text for k in mid):
        sev = 3
    if any(k in text for k in strong):
        sev = 4
    if "封号" in text or ("无法" in text and any(k in text for k in ["侧边栏", "电竞模式", "游戏助手"])):
        sev = 5

    if s == "neutral":
        sev = max(1, sev - 1)

    return s, int(sev)


def extract_tieba_name(url: str) -> str:
    # Best-effort: /f?kw=xxx or /f?ie=utf-8&kw=xxx
    try:
        p = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(p.query)
        if "kw" in qs and qs["kw"]:
            return qs["kw"][0]
    except Exception:
        pass
    return ""


def run(limit: int = 20, sleep_s: float = 0.8) -> Tuple[List[Item], Dict[str, int]]:
    queries = build_queries()

    # Collect raw results
    seen_urls = set()
    items: List[Item] = []
    fetched = 0

    for q in queries:
        if len(items) >= limit:
            break
        query = q
        # Add exclusions into the query as a hint
        query_with_excl = query + " " + " ".join([f"-{t}" for t in ["外挂", "脚本", "修改器"]])
        url = "https://cn.bing.com/search?" + urllib.parse.urlencode({"q": query_with_excl, "ensearch": "0"})

        try:
            page = _http_get(url)
            fetched += 1
        except Exception:
            continue

        results = _extract_bing_results(page)
        for r in results:
            if len(items) >= limit:
                break
            ru = normalize_url(r.get("url", ""))
            if not ru or ru in seen_urls:
                continue
            # Keep only tieba
            if "tieba.baidu.com" not in ru:
                continue

            title = r.get("title", "").strip()
            snippet = r.get("snippet", "").strip()
            text = f"{title} {snippet}"

            relevance, hit_kws, keep = compute_relevance(text)
            cat = classify(text)
            sent, sev = sentiment_and_severity(text)

            # If not keep, still include during test but mark
            tieba_name = extract_tieba_name(ru)

            conclusion = ""
            if keep:
                conclusion = "疑似与 OPPO/一加/ColorOS 游戏助手相关的问题/反馈，建议跟进。"
            else:
                conclusion = "相关性较低或疑似噪声（测试期保留记录）。"

            items.append(
                Item(
                    platform=PLATFORM,
                    search_term=q,
                    tieba_name=tieba_name,
                    title=title,
                    summary=snippet,
                    publish_time="",
                    url=ru,
                    reply_count="",
                    relevance=relevance,
                    keep=bool(keep),
                    category=cat,
                    sentiment=sent,
                    severity=sev,
                    hit_keywords=hit_kws,
                    conclusion=conclusion,
                )
            )
            seen_urls.add(ru)

        time.sleep(sleep_s)

    stats = {
        "total": len(items),
        "kept": sum(1 for x in items if x.keep),
        "negative": sum(1 for x in items if x.sentiment == "negative" and x.keep),
        "high_sev": sum(1 for x in items if x.severity >= 4 and x.keep),
    }

    return items, stats


def write_outputs(items: List[Item], stats: Dict[str, int], out_dir: str) -> Tuple[str, str, str]:
    os.makedirs(out_dir, exist_ok=True)
    day = dt.datetime.now().strftime("%Y%m%d")
    base = os.path.join(out_dir, f"tieba_oppo_daily_{day}")
    jsonl_path = base + ".jsonl"
    csv_path = base + ".csv"
    md_path = base + ".md"

    # JSONL
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(dataclasses.asdict(it), ensure_ascii=False) + "\n")

    # CSV
    fields = [
        "platform",
        "search_term",
        "tieba_name",
        "title",
        "summary",
        "publish_time",
        "url",
        "reply_count",
        "relevance",
        "keep",
        "category",
        "sentiment",
        "severity",
        "hit_keywords",
        "conclusion",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for it in items:
            d = dataclasses.asdict(it)
            d["hit_keywords"] = "|".join(it.hit_keywords)
            w.writerow(d)

    # Markdown daily report
    kept = [x for x in items if x.keep]
    top5 = sorted(kept, key=lambda x: (x.severity, x.relevance), reverse=True)[:5]

    cat_dist: Dict[str, int] = {}
    for x in kept:
        cat_dist[x.category] = cat_dist.get(x.category, 0) + 1

    md_lines = []
    md_lines.append(f"# OPPO 游戏助手 · 百度贴吧舆情日报（测试版）\n")
    md_lines.append(f"- 主题：{TOPIC}")
    md_lines.append(f"- 日期：{dt.datetime.now().strftime('%Y-%m-%d')}")
    md_lines.append("\n## 今日概览")
    md_lines.append(f"- 今日抓取总量：{stats.get('total', 0)}")
    md_lines.append(f"- 今日相关内容总量（keep=true）：{stats.get('kept', 0)}")
    md_lines.append(f"- 今日负面内容总量（keep 且 negative）：{stats.get('negative', 0)}")
    md_lines.append(f"- 高严重度内容数量（keep 且 severity>=4）：{stats.get('high_sev', 0)}")

    md_lines.append("\n## 分类分布（keep=true）")
    if cat_dist:
        for k, v in sorted(cat_dist.items(), key=lambda kv: kv[1], reverse=True):
            md_lines.append(f"- {k}：{v}")
    else:
        md_lines.append("- （暂无）")

    md_lines.append("\n## 重点舆情 TOP5（keep=true）")
    if top5:
        for i, x in enumerate(top5, 1):
            md_lines.append(f"{i}. [{x.title}]({x.url})")
            md_lines.append(f"   - 分类：{x.category} | 情绪：{x.sentiment} | 严重度：{x.severity} | 相关性：{x.relevance}")
            md_lines.append(f"   - 命中：{'、'.join(x.hit_keywords[:12])}")
            if x.summary:
                md_lines.append(f"   - 摘要：{x.summary}")
    else:
        md_lines.append("- （暂无）")

    md_lines.append("\n## 今日观察结论")
    if stats.get("kept", 0) == 0:
        md_lines.append("- 今日在搜索结果中未发现高相关问题反馈（可能受搜索覆盖/反爬影响）。")
    else:
        md_lines.append("- 今日存在一定量与 OPPO/一加/ColorOS 游戏助手相关的用户反馈与求助，建议优先处理严重度≥4 的条目。")
    md_lines.append("\n---\n")
    md_lines.append("备注：本测试版基于搜索引擎结果页的标题/摘要进行判定，未直接抓取帖子正文（用于绕过贴吧安全验证）。")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    return jsonl_path, csv_path, md_path


def main(argv: List[str]) -> int:
    limit = 20
    out_dir = os.path.join(os.path.dirname(__file__), "..", "out")

    if "--limit" in argv:
        try:
            limit = int(argv[argv.index("--limit") + 1])
        except Exception:
            pass

    items, stats = run(limit=limit)
    jsonl_path, csv_path, md_path = write_outputs(items, stats, out_dir=os.path.abspath(out_dir))

    print(json.dumps({"jsonl": jsonl_path, "csv": csv_path, "md": md_path, "stats": stats}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
