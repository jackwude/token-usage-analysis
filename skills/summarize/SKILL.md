---
name: summarize
description: 使用 summarize CLI 快速总结 URL、PDF、图片、音频、YouTube 视频。当用户说"总结一下这个链接/文章/PDF"、"帮我总结 [URL]"、或直接发 URL 并说"总结"时触发。
homepage: https://summarize.sh
metadata: {"clawdbot":{"emoji":"🧾","requires":{"bins":["summarize"]},"install":[{"id":"brew","kind":"brew","formula":"steipete/tap/summarize","bins":["summarize"],"label":"Install summarize (brew)"}]}}
---

# Summarize

使用 summarize CLI 快速总结 URL、本地文件、YouTube 视频。

## 🎯 触发条件

**当用户出现以下任一行为时，自动触发此 skill：**

| 用户话术 | 示例 |
|---------|------|
| 总结链接/文章 | "总结一下这个链接：https://..." |
| 帮我总结 | "帮我总结这篇文章" |
| 直接发 URL + 总结 | "https://... 总结" |
| 总结文件 | "总结这个 PDF：/path/to/file.pdf" |
| 总结视频 | "总结一下这个 YouTube 视频" |

**支持的内容类型：**
- ✅ 网页文章（URL）
- ✅ PDF 文档
- ✅ 图片（OCR + 描述）
- ✅ 音频文件（转写 + 总结）
- ✅ YouTube 视频

---

## Quick start

```bash
summarize "https://example.com" --model google/gemini-3-flash-preview
summarize "/path/to/file.pdf" --model google/gemini-3-flash-preview
summarize "https://youtu.be/dQw4w9WgXcQ" --youtube auto
```

## Model + keys

Set the API key for your chosen provider:
- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- xAI: `XAI_API_KEY`
- Google: `GEMINI_API_KEY` (aliases: `GOOGLE_GENERATIVE_AI_API_KEY`, `GOOGLE_API_KEY`)

Default model is `google/gemini-3-flash-preview` if none is set.

## Useful flags

- `--length short|medium|long|xl|xxl|<chars>`
- `--max-output-tokens <count>`
- `--extract-only` (URLs only)
- `--json` (machine readable)
- `--firecrawl auto|off|always` (fallback extraction)
- `--youtube auto` (Apify fallback if `APIFY_API_TOKEN` set)

## Config

Optional config file: `~/.summarize/config.json`

```json
{ "model": "openai/gpt-5.2" }
```

Optional services:
- `FIRECRAWL_API_KEY` for blocked sites
- `APIFY_API_TOKEN` for YouTube fallback

---

## 🔧 环境检查（执行前）

执行总结任务前，自动检查：

1. **CLI 是否安装**：`which summarize`
   - ❌ 未安装 → 提示用户运行 `brew install steipete/tap/summarize`
2. **API Key 是否配置**：检查至少一个 API Key
   - ❌ 未配置 → 提示用户配置 `OPENAI_API_KEY` 或 `GEMINI_API_KEY` 等
3. **模型配置**：读取 `~/.summarize/config.json` 或使用默认模型

---

## 📋 使用示例

**总结网页：**
```
总结一下这个链接：https://example.com/article
```

**总结 PDF：**
```
总结这个 PDF：~/Documents/report.pdf
```

**总结 YouTube：**
```
总结一下这个视频：https://youtu.be/xxx
```

**自定义长度：**
```
总结这篇文章，要简短一点
```

---

## ⚠️ 降级策略

| 问题 | 处理方式 |
|------|---------|
| CLI 未安装 | 提示安装命令，建议用 `brew install` |
| API Key 缺失 | 提示配置对应的 API Key |
| 网页无法访问 | 尝试 `--firecrawl auto` 兜底提取 |
| 内容过长 | 自动截断，提示用户使用 `--length short` |
| YouTube 无法解析 | 检查 `APIFY_API_TOKEN` 是否配置 |

---

## 🎛️ 当前配置

**默认模型：** `openai/doubao-seed-2-0-pro-260215`（火山引擎豆包）

**配置文件：** `~/.summarize/config.json`
