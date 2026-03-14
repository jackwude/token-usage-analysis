#!/usr/bin/env python3
"""
微信公众号文章解析工具
用法：python3 wechat-article.py <文章链接>
"""

import sys
import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify


def parse_wechat_article(url: str) -> dict:
    """解析微信公众号文章，返回标题和内容"""
    
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.43",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    
    try:
        with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as client:
            resp = client.get(url)
            
            if resp.status_code != 200:
                return {"success": False, "error": f"请求失败：HTTP {resp.status_code}"}
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 检查是否是验证页面
            if "环境异常" in resp.text or "验证码" in resp.text:
                return {"success": False, "error": "微信反爬验证，需要人工验证"}
            
            # 提取标题
            title = soup.find('h2', id='activity-name')
            if not title:
                title = soup.find('h1', class_='rich_media_title')
            if not title:
                title = soup.find('title')
            
            title_text = title.get_text(strip=True) if title else "未知标题"
            
            # 提取作者/来源
            author = soup.find('div', class_='rich_media_meta_nickname')
            author_text = author.get_text(strip=True) if author else "未知来源"
            
            # 提取正文
            content = soup.find('div', id='js_content')
            
            if not content:
                return {"success": False, "error": "无法提取正文内容"}
            
            # 转 Markdown
            md_content = markdownify(str(content), heading_style="ATX")
            
            return {
                "success": True,
                "title": title_text,
                "author": author_text,
                "url": url,
                "content": md_content
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def summarize_content(content: str, max_length: int = 2000) -> str:
    """提取内容摘要（简单版：取前 N 字符）"""
    if len(content) <= max_length:
        return content
    return content[:max_length] + "\n\n...（内容过长，已截断）"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python3 wechat-article.py <文章链接>")
        sys.exit(1)
    
    url = sys.argv[1]
    result = parse_wechat_article(url)
    
    if result["success"]:
        print(f"✅ 标题：{result['title']}")
        print(f"📝 来源：{result['author']}")
        print(f"🔗 链接：{result['url']}")
        print("\n" + "="*50 + "\n")
        print(result['content'][:3000])
    else:
        print(f"❌ 解析失败：{result['error']}")
        sys.exit(1)
