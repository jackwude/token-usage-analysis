#!/usr/bin/env python3
"""
火山引擎豆包图像生成脚本
使用 doubao-seedream-5-0-260128 模型生成高质量图片
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path


def slugify(text: str) -> str:
    """将文本转换为文件名友好的格式"""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fa5]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "image"


def default_out_dir() -> Path:
    """获取默认输出目录"""
    now = dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    preferred = Path.home() / "Projects" / "tmp"
    base = preferred if preferred.is_dir() else Path("./tmp")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"volc-doubao-image-gen-{now}"


def validate_size(size: str) -> bool:
    """验证尺寸是否符合火山引擎要求 (≥ 3686400 像素)"""
    try:
        width, height = map(int, size.lower().split("x"))
        return width * height >= 3686400
    except (ValueError, AttributeError):
        return False


def request_images(
    api_key: str,
    base_url: str,
    prompt: str,
    model: str,
    size: str,
) -> dict:
    """调用火山引擎图像生成 API"""
    url = f"{base_url}/images/generations"
    
    args = {
        "model": model,
        "prompt": prompt,
        "size": size,
    }
    
    body = json.dumps(args).encode("utf-8")
    req = urllib.request.Request(
        url,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=body,
    )
    
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        payload = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"火山引擎 API 错误 ({e.code}): {payload}") from e


def write_gallery(out_dir: Path, items: list[dict]) -> None:
    """生成 HTML 画廊"""
    thumbs = "\n".join(
        [
            f"""
<figure>
  <a href="{html_escape(it["file"], quote=True)}"><img src="{html_escape(it["file"], quote=True)}" loading="lazy" /></a>
  <figcaption>{html_escape(it["prompt"])}</figcaption>
</figure>
""".strip()
            for it in items
        ]
    )
    html = f"""<!doctype html>
<meta charset="utf-8" />
<title>volc-doubao-image-gen</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 24px; font: 14px/1.4 ui-sans-serif, system-ui; background: #0b0f14; color: #e8edf2; }}
  h1 {{ font-size: 18px; margin: 0 0 16px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }}
  figure {{ margin: 0; padding: 12px; border: 1px solid #1e2a36; border-radius: 14px; background: #0f1620; }}
  img {{ width: 100%; height: auto; border-radius: 10px; display: block; }}
  figcaption {{ margin-top: 10px; color: #b7c2cc; }}
  code {{ color: #9cd1ff; }}
</style>
<h1>🎨 豆包图像生成</h1>
<p>输出目录：<code>{html_escape(out_dir.as_posix())}</code></p>
<div class="grid">
{thumbs}
</div>
"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")


def html_escape(text: str, quote: bool = True) -> str:
    """HTML 转义"""
    from html import escape
    return escape(text, quote=quote)


def main() -> int:
    ap = argparse.ArgumentParser(description="火山引擎豆包图像生成 API")
    ap.add_argument("--prompt", required=True, help="图片描述提示词")
    ap.add_argument("--count", type=int, default=1, help="生成图片数量 (默认 1)")
    ap.add_argument("--model", default="doubao-seedream-5-0-260128", help="模型 ID")
    ap.add_argument("--size", default="1920x1920", help="图片尺寸 (必须 ≥ 3686400 像素)")
    ap.add_argument("--out-dir", default="", help="输出目录")
    args = ap.parse_args()
    
    # 获取 API 配置
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    base_url = (os.environ.get("OPENAI_BASE_URL") or "https://ark.cn-beijing.volces.com/api/v3").strip()
    
    if not api_key:
        print("❌ 错误：缺少 OPENAI_API_KEY 环境变量", file=sys.stderr)
        return 2
    
    # 验证尺寸
    if not validate_size(args.size):
        print(f"❌ 错误：尺寸 {args.size} 不符合要求，必须 ≥ 3686400 像素", file=sys.stderr)
        print("   推荐尺寸：1920x1920, 2048x2048, 2560x2560", file=sys.stderr)
        return 2
    
    # 设置输出目录
    out_dir = Path(args.out_dir).expanduser() if args.out_dir else default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🎨 开始生成图片...")
    print(f"   模型：{args.model}")
    print(f"   尺寸：{args.size}")
    print(f"   数量：{args.count}")
    print(f"   输出：{out_dir}")
    print()
    
    items: list[dict] = []
    
    for idx in range(1, args.count + 1):
        print(f"[{idx}/{args.count}] {args.prompt}")
        
        try:
            res = request_images(
                api_key,
                base_url,
                args.prompt,
                args.model,
                args.size,
            )
            
            if "error" in res:
                raise RuntimeError(f"API 错误：{res['error']}")
            
            data = res.get("data", [{}])[0]
            image_url = data.get("url")
            
            if not image_url:
                raise RuntimeError(f"未返回图片 URL: {json.dumps(res)[:400]}")
            
            # 下载图片
            filename = f"{idx:03d}-{slugify(args.prompt)[:40]}.png"
            filepath = out_dir / filename
            
            urllib.request.urlretrieve(image_url, filepath)
            
            items.append({"prompt": args.prompt, "file": filename})
            print(f"   ✅ 已保存：{filename}")
            
        except Exception as e:
            print(f"   ❌ 失败：{e}", file=sys.stderr)
            continue
    
    if not items:
        print("\n❌ 所有图片生成失败", file=sys.stderr)
        return 1
    
    # 保存元数据
    (out_dir / "prompts.json").write_text(
        json.dumps(items, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # 生成画廊
    write_gallery(out_dir, items)
    
    print(f"\n✅ 完成！生成 {len(items)} 张图片")
    print(f"📁 输出目录：{out_dir}")
    print(f"🖼️  画廊：{(out_dir / 'index.html').as_posix()}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
