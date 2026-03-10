#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OPPO 游戏助手 · 百度贴吧舆情采集（测试版）

策略：用 Bing 搜索 site:tieba.baidu.com 绕过贴吧滑块验证
输出：JSONL + CSV + Markdown 日报
"""

import csv
import datetime as dt
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

# ================= 配置区 =================

PLATFORM = "百度贴吧"
TOPIC = "OPPO 游戏助手"
OUT_DIR = Path(__file__).parent.parent / "out" / "tieba_oppo"

# 核心词（高权重）
CORE_TERMS = [
    "OPPO 游戏助手", "OPPO 游戏助手", "一加游戏助手", "一加 游戏助手",
    "ColorOS 游戏助手", "游戏侧边栏", "OPPO 侧边栏", "一加 侧边栏",
    "电竞模式", "云加速", "旁路供电",
]

# 问题词
PROBLEM_TERMS = [
    "卡顿", "掉帧", "锁 30 帧", "只有 60 帧", "120 帧", "发热",
    "失效", "没了", "消失", "调不出来", "划不动", "扫不出来",
    "不支持", "失灵", "广告", "封号", "异常", "bug", "问题",
    "关闭", "卸载", "更新后",
]

# 意图词
INTENT_TERMS = [
    "为什么", "怎么办", "求救", "求解决", "什么情况", "有人遇到吗",
    "避坑", "反馈", "建议", "希望增加", "怎么关闭", "怎么卸载",
]

# 排除词（命中则丢弃）
EXCLUDE_TERMS = ["外挂", "脚本", "辅助器", "模拟器", "修改器", "代练"]

# 游戏名（用于组合搜索）
GAMES = ["王者荣耀", "原神", "三角洲行动", "和平精英", "崩坏星穹铁道"]

# 分类规则
CATEGORY_RULES = [
    ("功能异常", ["失效", "消失", "没了", "调不出来", "失灵", "不支持"]),
    ("性能帧率", ["卡顿", "掉帧", "锁 30 帧", "只有 60 帧", "120 帧", "发热"]),
    ("更新回归", ["更新后", "更新"]),
    ("广告争议", ["广告"]),
    ("兼容识别", ["不支持", "识别", "扫不出来"]),
    ("风险封号", ["封号", "风险"]),
    ("关闭卸载", ["关闭", "卸载", "怎么关闭", "怎么卸载"]),
    ("用户建议", ["建议", "希望增加", "反馈"]),
]

NEGATIVE_HINTS = PROBLEM_TERMS + ["吐槽", "垃圾", "离谱", "烦", "坑", "难用", "崩溃", "无法", "不能"]
POSITIVE_HINTS = ["解决", "已解决", "搞定", "好用", "赞", "推荐"]


# ================= 工具函数 =================

def http_get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_bing_results(html_text: str):
    """解析 Bing 搜索结果页"""
    results = []
    pat = r"<li[^>]*class=\"b_algo\"[^>]*>"
    blocks = re.split(pat, html_text)

    for b in blocks[1:]:
        # 标题 + URL
        m = re.search(r"<h2[^>]*>\s*<a[^>]+href=\"([^\"]+)\"[^>]*>([\s\S]*?)</a>", b)
        if not m:
            continue
        url = html.unescape(m.group(1))
        title = strip_tags(m.group(2))

        # 摘要
        sm = re.search(r"class=\"b_caption\"[\s\S]*?<p>([\s\S]*?)</p>", b)
        snippet = strip_tags(sm.group(1)) if sm else ""
        if not snippet:
            sm2 = re.search(r"<p>([\s\S]*?)</p>", b)
            snippet = strip_tags(sm2.group(1)) if sm2 else ""

        results.append({"title": title, "snippet": snippet, "url": url})

    return results


def extract_tieba_name(url: str) -> str:
    """从 URL 提取贴吧名"""
    try:
        p = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(p.query)
        if "kw" in qs and qs["kw"]:
            return qs["kw"][0]
    except Exception:
        pass
    return ""


def normalize_url(u: str) -> str:
    """标准化 URL"""
    if "bing.com" in u and "r=" in u:
        try:
            parsed = urllib.parse.urlparse(u)
            qs = urllib.parse.parse_qs(parsed.query)
            if "r" in qs:
                return qs["r"][0]
        except Exception:
            pass
    return u


# ================= 判定逻辑 =================

def compute_relevance(text: str):
    """计算相关性分数"""
    hits = []

    def hit_any(terms):
        c = 0
        for t in terms:
            if t and t in text:
                hits.append(t)
                c += 1
        return c

    # 排除词命中 → 直接丢弃
    if any(t in text for t in EXCLUDE_TERMS):
        return 0.0, hits, False

    core_hits = hit_any(CORE_TERMS)
    prob_hits = hit_any(PROBLEM_TERMS)
    intent_hits = hit_any(INTENT_TERMS)

    # 品牌/特征检测
    has_generic = "游戏助手" in text
    has_brand = any(k in text for k in ["OPPO", "一加", "ColorOS", "侧边栏", "电竞模式", "云加速", "旁路供电"])

    score = 0.0
    score += min(core_hits, 3) * 1.6
    score += min(prob_hits, 3) * 1.2
    score += min(intent_hits, 2) * 0.6

    # 只有"游戏助手"但无品牌特征 → 降权
    if has_generic and not has_brand:
        score *= 0.35

    # 保留条件
    keep = score >= 2.2 and core_hits > 0 and prob_hits > 0
    # 强特征 + 问题 → 放宽
    if any(k in text for k in ["电竞模式", "游戏侧边栏", "旁路供电", "云加速"]) and prob_hits > 0:
        keep = score >= 1.8

    return round(score, 2), sorted(set(hits)), keep


def classify(text: str) -> str:
    """分类"""
    for cat, kws in CATEGORY_RULES:
        if any(k in text for k in kws):
            return cat
    if any(k in text for k in PROBLEM_TERMS):
        return "功能异常"
    return "用户建议"


def sentiment_and_severity(text: str):
    """情绪 + 严重度"""
    sent = "neutral"
    if any(k in text for k in POSITIVE_HINTS):
        sent = "positive"
    if any(k in text for k in NEGATIVE_HINTS) or any(k in text for k in INTENT_TERMS):
        sent = "negative"

    sev = 2
    strong = ["无法", "不能", "完全", "彻底", "失效", "封号", "崩溃", "严重", "更新后"]
    mid = ["卡顿", "掉帧", "发热", "异常", "bug", "广告", "消失", "调不出来"]

    if any(k in text for k in mid):
        sev = 3
    if any(k in text for k in strong):
        sev = 4
    if "封号" in text or ("无法" in text and any(k in text for k in ["侧边栏", "电竞模式", "游戏助手"])):
        sev = 5

    if sent == "neutral":
        sev = max(1, sev - 1)

    return sent, int(sev)


# ================= 搜索查询构建 =================

def build_queries():
    """构建搜索查询列表"""
    queries = []

    # 1. 高精度核心词
    for core in ["OPPO 游戏助手", "一加 游戏助手", "ColorOS 游戏助手", "游戏侧边栏", "电竞模式", "云加速", "旁路供电"]:
        queries.append(f"site:tieba.baidu.com {core}")

    # 2. 核心 + 问题
    for core in ["OPPO 游戏助手", "一加 游戏助手", "ColorOS 游戏助手", "游戏侧边栏", "电竞模式", "云加速", "旁路供电"]:
        for prob in ["卡顿", "掉帧", "失效", "消失", "调不出来", "广告", "封号", "卸载", "更新后"]:
            queries.append(f"site:tieba.baidu.com {core} {prob}")

    # 3. 核心 + 游戏名
    for core in ["OPPO 游戏助手", "游戏侧边栏", "电竞模式", "云加速", "旁路供电"]:
        for g in GAMES:
            queries.append(f"site:tieba.baidu.com {core} {g}")

    return queries


# ================= 主采集流程 =================

def collect(limit=20, sleep_s=0.8):
    """执行采集（带进度输出）"""
    queries = build_queries()
    seen_urls = set()
    items = []
    fetched = 0

    print(f"总查询数：{len(queries)}；目标条数：{limit}\n", flush=True)

    for idx, q in enumerate(queries, 1):
        if len(items) >= limit:
            break

        print(f"[{idx}/{len(queries)}] 搜索：{q}", flush=True)

        # 加排除词到查询
        q_excl = q + " " + " ".join([f"-{t}" for t in ["外挂", "脚本", "修改器"]])
        url = "https://cn.bing.com/search?" + urllib.parse.urlencode({"q": q_excl, "ensearch": "0"})

        try:
            page = http_get(url)
            fetched += 1
        except Exception as e:
            print(f"  搜索失败：{q[:60]}... → {e}", flush=True)
            continue

        results = extract_bing_results(page)
        print(f"  解析到候选结果：{len(results)}", flush=True)

        added = 0
        for r in results:
            if len(items) >= limit:
                break

            ru = normalize_url(r.get("url", ""))
            if not ru or ru in seen_urls:
                continue
            if "tieba.baidu.com" not in ru:
                continue

            title = r.get("title", "").strip()
            snippet = r.get("snippet", "").strip()
            text = f"{title} {snippet}"

            relevance, hit_kws, keep = compute_relevance(text)
            cat = classify(text)
            sent, sev = sentiment_and_severity(text)
            tieba_name = extract_tieba_name(ru)

            conclusion = "疑似与 OPPO/一加/ColorOS 游戏助手相关的问题/反馈，建议跟进。" if keep else "相关性较低或疑似噪声（测试期保留记录）。"

            items.append({
                "platform": PLATFORM,
                "search_term": q,
                "tieba_name": tieba_name,
                "title": title,
                "summary": snippet,
                "publish_time": "",
                "url": ru,
                "reply_count": "",
                "relevance": relevance,
                "keep": bool(keep),
                "category": cat,
                "sentiment": sent,
                "severity": sev,
                "hit_keywords": hit_kws,
                "conclusion": conclusion,
            })
            seen_urls.add(ru)
            added += 1

        print(f"  本次新增：{added}；累计：{len(items)}/{limit}\n", flush=True)
        time.sleep(sleep_s)

    stats = {
        "total": len(items),
        "kept": sum(1 for x in items if x["keep"]),
        "negative": sum(1 for x in items if x["sentiment"] == "negative" and x["keep"]),
        "high_sev": sum(1 for x in items if x["severity"] >= 4 and x["keep"]),
    }

    return items, stats, fetched


# ================= 输出 =================

def write_outputs(items, stats, fetched):
    """输出文件"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    day = dt.datetime.now().strftime("%Y%m%d")
    base = OUT_DIR / f"tieba_oppo_daily_{day}"

    # JSONL
    jsonl_path = base.with_suffix(".jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    # CSV
    csv_path = base.with_suffix(".csv")
    fields = ["platform", "search_term", "tieba_name", "title", "summary", "publish_time",
              "url", "reply_count", "relevance", "keep", "category", "sentiment",
              "severity", "hit_keywords", "conclusion"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for it in items:
            d = dict(it)
            d["hit_keywords"] = "|".join(it["hit_keywords"])
            w.writerow(d)

    # Markdown 日报
    md_path = base.with_suffix(".md")
    kept = [x for x in items if x["keep"]]
    top5 = sorted(kept, key=lambda x: (x["severity"], x["relevance"]), reverse=True)[:5]

    cat_dist = {}
    for x in kept:
        cat_dist[x["category"]] = cat_dist.get(x["category"], 0) + 1

    md_lines = [
        f"# OPPO 游戏助手 · 百度贴吧舆情日报（测试版）",
        f"- 主题：{TOPIC}",
        f"- 日期：{dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 今日概览",
        f"- 今日抓取总量：{stats.get('total', 0)}",
        f"- 今日相关内容总量（keep=true）：{stats.get('kept', 0)}",
        f"- 今日负面内容总量（keep 且 negative）：{stats.get('negative', 0)}",
        f"- 高严重度内容数量（keep 且 severity>=4）：{stats.get('high_sev', 0)}",
        f"- 实际搜索次数：{fetched}",
        "",
        "## 分类分布（keep=true）",
    ]

    if cat_dist:
        for k, v in sorted(cat_dist.items(), key=lambda kv: kv[1], reverse=True):
            md_lines.append(f"- {k}：{v}")
    else:
        md_lines.append("- （暂无）")

    md_lines.extend(["", "## 重点舆情 TOP5（keep=true）"])
    if top5:
        for i, x in enumerate(top5, 1):
            md_lines.append(f"{i}. [{x['title']}]({x['url']})")
            md_lines.append(f"   - 分类：{x['category']} | 情绪：{x['sentiment']} | 严重度：{x['severity']} | 相关性：{x['relevance']}")
            md_lines.append(f"   - 命中：{'、'.join(x['hit_keywords'][:12])}")
            if x["summary"]:
                md_lines.append(f"   - 摘要：{x['summary']}")
    else:
        md_lines.append("- （暂无）")

    md_lines.extend(["", "## 今日观察结论"])
    if stats.get("kept", 0) == 0:
        md_lines.append("- 今日在搜索结果中未发现高相关问题反馈（可能受搜索覆盖/反爬影响）。")
    else:
        md_lines.append("- 今日存在一定量与 OPPO/一加/ColorOS 游戏助手相关的用户反馈与求助，建议优先处理严重度≥4 的条目。")

    md_lines.extend([
        "",
        "---",
        "备注：本测试版基于搜索引擎结果页的标题/摘要进行判定，未直接抓取帖子正文（用于绕过贴吧安全验证）。",
    ])

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    return jsonl_path, csv_path, md_path


# ================= 入口 =================

def main():
    print("📚 开始执行 OPPO 游戏助手 · 百度贴吧舆情采集（测试版）...")
    print(f"   目标：抓取 20 条左右相关帖子")
    print(f"   策略：Bing 搜索 site:tieba.baidu.com 绕过反爬")
    print()

    items, stats, fetched = collect(limit=20, sleep_s=0.8)
    jsonl_path, csv_path, md_path = write_outputs(items, stats, fetched)

    print(f"✅ 采集完成！")
    print(f"   搜索次数：{fetched}")
    print(f"   抓取总量：{stats['total']}")
    print(f"   相关内容：{stats['kept']}")
    print(f"   负面内容：{stats['negative']}")
    print(f"   高严重度：{stats['high_sev']}")
    print()
    print(f"📁 输出文件：")
    print(f"   JSONL: {jsonl_path}")
    print(f"   CSV:   {csv_path}")
    print(f"   MD:    {md_path}")

    return items, stats


if __name__ == "__main__":
    main()
