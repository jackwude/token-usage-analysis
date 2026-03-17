# 🎨 豆包图像生成 Skill - 部署完成

## ✅ 完成情况

### 1. Skill 创建
- **位置**: `~/.openclaw/workspace/skills/volc-doubao-image-gen/`
- **文件**:
  - `SKILL.md` - Skill 定义和元数据
  - `scripts/gen.py` - 图像生成脚本
  - `README.md` - 使用指南

### 2. 全局共享
已为所有 Agent 创建符号链接：
- ✅ `main` (麻辣小龙虾 🦞)
- ✅ `tg-office`
- ✅ `agent-creator`
- ✅ `data-collector`

### 3. 测试验证
- ✅ API 调用成功
- ✅ 图片生成正常
- ✅ 尺寸验证正确
- ✅ 画廊生成 OK

## 🚀 使用方式

### 对话触发（推荐）
直接告诉任意 Agent：
```
帮我生成一张小萨摩耶的图片
画一个可爱的猫咪
图片生成：赛博朋克城市夜景
```

### 命令行
```bash
python3 ~/.openclaw/workspace/skills/volc-doubao-image-gen/scripts/gen.py \
  --prompt "一只可爱的小狗" \
  --size "2048x2048"
```

## 📋 配置要点

| 参数 | 值 | 说明 |
|------|-----|------|
| 模型 | `doubao-seedream-5-0-260128` | 火山引擎豆包 |
| API Key | `OPENAI_API_KEY` | 火山引擎 API Key |
| Base URL | `https://ark.cn-beijing.volces.com/api/v3` | 火山引擎端点 |
| 最小尺寸 | `1920x1920` | ≥ 3686400 像素 |

## 📝 Git 提交

```
1c130de - feat: 添加火山引擎豆包图像生成 Skill
a76bc0b - docs: 添加豆包图像生成 Skill 使用指南
```

## 🎯 下一步

所有 Agent 现在都可以使用豆包图像生成能力！

用户可以直接对话触发，无需记忆命令。
