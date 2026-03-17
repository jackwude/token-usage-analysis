---
name: volc-doubao-image-gen
description: 火山引擎豆包图像生成 API。支持 doubao-seedream-5-0-260128 模型，生成高质量图片。
metadata:
  {
    "openclaw":
      {
        "emoji": "🎨",
        "requires": { "bins": ["python3"], "env": ["OPENAI_API_KEY", "OPENAI_BASE_URL"] },
        "primaryEnv": "OPENAI_API_KEY",
        "install":
          [
            {
              "id": "python-brew",
              "kind": "brew",
              "formula": "python",
              "bins": ["python3"],
              "label": "Install Python (brew)",
            },
          ],
      },
  }
---

# 火山引擎豆包图像生成

使用火山引擎豆包 Seedream 5.0 模型生成高质量图片。

## 配置要求

- **API Key**: `OPENAI_API_KEY` (火山引擎 API Key)
- **Base URL**: `OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3`
- **模型**: `doubao-seedream-5-0-260128`

## 运行

```bash
python3 {baseDir}/scripts/gen.py
```

### 参数说明

```bash
# 基础用法 - 生成 1 张图片
python3 {baseDir}/scripts/gen.py --prompt "一只可爱的小萨摩耶幼犬"

# 指定尺寸 (必须 ≥ 3686400 像素)
python3 {baseDir}/scripts/gen.py --prompt "描述" --size "1920x1920"
python3 {baseDir}/scripts/gen.py --prompt "描述" --size "2048x2048"

# 生成多张图片
python3 {baseDir}/scripts/gen.py --prompt "描述" --count 4

# 指定输出目录
python3 {baseDir}/scripts/gen.py --prompt "描述" --out-dir ./my-images
```

### 可用尺寸

火山引擎要求图片总像素必须 **≥ 3686400**：

| 尺寸 | 总像素 | 推荐度 |
|------|--------|--------|
| `1920x1920` | 3,686,400 | ✅ 最小可用 |
| `2048x2048` | 4,194,304 | ✅ 推荐 |
| `2560x2560` | 6,553,600 | ✅ 高质量 |
| `1024x1024` | 1,048,576 | ❌ 太小 |

## 输出

- `*.png` 图片文件
- `prompts.json` (提示词 → 文件映射)
- `index.html` (缩略图画廊)

## 示例

```bash
# 生成小萨摩耶
python3 {baseDir}/scripts/gen.py --prompt "一只可爱的小萨摩耶幼犬，白色蓬松毛发，微笑表情，坐在草地上，阳光明媚"

# 生成风景照
python3 {baseDir}/scripts/gen.py --prompt "宁静的湖面，倒映着雪山和蓝天白云，清晨阳光" --size "2048x2048"

# 批量生成 4 张
python3 {baseDir}/scripts/gen.py --prompt "赛博朋克风格的城市夜景" --count 4
```

## 注意事项

1. **尺寸限制**: 必须 ≥ 3686400 像素，否则会返回 `InvalidParameter` 错误
2. **生成时间**: 约 15-30 秒/张，建议设置 exec timeout=300
3. **Token 消耗**: 约 14400 tokens/张 (1920x1920)
4. **输出格式**: 固定为 PNG 格式

## 与其他 Agent 共享

此 Skill 位于全局 skills 目录，所有 Agent 均可使用：
- `main` (麻辣小龙虾)
- `tg-office`
- `agent-creator`
- `data-collector`

调用方式：直接使用快捷命令或让 Agent 调用此 Skill。
