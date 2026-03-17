# 🎨 豆包图像生成 Skill 使用指南

## 快速开始

### 方式 1: 直接对话（推荐）

直接告诉 Agent 你想要生成什么图片：

```
帮我生成一张小萨摩耶的图片
画一个可爱的猫咪
图片生成：赛博朋克城市夜景
```

Agent 会自动调用 `volc-doubao-image-gen` Skill。

### 方式 2: 命令行

```bash
# 基础用法
python3 ~/.openclaw/workspace/skills/volc-doubao-image-gen/scripts/gen.py --prompt "一只可爱的小狗"

# 指定尺寸
python3 ~/.openclaw/workspace/skills/volc-doubao-image-gen/scripts/gen.py --prompt "风景" --size "2048x2048"

# 批量生成
python3 ~/.openclaw/workspace/skills/volc-doubao-image-gen/scripts/gen.py --prompt "花朵" --count 4
```

## 配置

Skill 已配置好环境变量，无需额外设置：
- ✅ `OPENAI_API_KEY` - 火山引擎 API Key
- ✅ `OPENAI_BASE_URL` - `https://ark.cn-beijing.volces.com/api/v3`
- ✅ 模型：`doubao-seedream-5-0-260128`

## 尺寸要求

**必须 ≥ 3686400 像素**，否则 API 会报错：

| 尺寸 | 总像素 | 推荐场景 |
|------|--------|----------|
| `1920x1920` | 3,686,400 | 日常使用（最小） |
| `2048x2048` | 4,194,304 | 推荐（平衡） |
| `2560x2560` | 6,553,600 | 高质量 |

## 可用 Agent

此 Skill 对所有 Agent 可用：
- ✅ `main` (麻辣小龙虾 🦞)
- ✅ `tg-office`
- ✅ `agent-creator`
- ✅ `data-collector`

## 输出

- **图片**: PNG 格式
- **画廊**: `index.html` (缩略图页面)
- **元数据**: `prompts.json` (提示词记录)

默认输出到 `~/Projects/tmp/volc-doubao-image-gen-<时间戳>/` 或 `./tmp/`

## 示例提示词

```
一只可爱的小萨摩耶幼犬，白色蓬松毛发，微笑表情，坐在草地上，阳光明媚

宁静的湖面，倒映着雪山和蓝天白云，清晨阳光，高清摄影

赛博朋克风格的城市夜景，霓虹灯，高楼大厦，未来感

温馨的房间角落，书架，咖啡杯，暖黄色灯光，治愈系

中国风山水画，远山，云雾，松树，水墨风格
```

## 注意事项

1. **生成时间**: 约 15-30 秒/张
2. **Token 消耗**: 约 14400 tokens/张 (1920x1920)
3. **失败重试**: 网络问题可重新运行命令
4. **图片保存**: 生成后及时备份重要图片

## 故障排查

### 报错 "InvalidParameter: image size must be at least 3686400 pixels"
→ 尺寸太小，改用 `1920x1920` 或更大

### 报错 "Missing OPENAI_API_KEY"
→ 检查环境变量是否配置

### 生成超时
→ 增加 timeout 参数或使用 `exec yieldMs=30000`

## 技能位置

```
~/.openclaw/workspace/skills/volc-doubao-image-gen/
├── SKILL.md          # 技能定义
└── scripts/
    └── gen.py        # 生成脚本
```
