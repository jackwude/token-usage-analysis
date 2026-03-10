# Whisper.cpp + Metal 实施方案 (B 方案)

**创建时间**: 2026-03-07 20:03
**目标**: 为 OpenClaw 在 macOS M1 Pro 上部署 whisper.cpp + Metal，实现全局语音转写能力（Telegram audio tool）
**状态**: 🟡 待用户确认

---

## 📋 方案对比

### 方案 A: brew 安装 (推荐)
```bash
brew install whisper-cpp
```
| 维度 | 说明 |
|------|------|
| **安装耗时** | ~2-3 分钟（含依赖） |
| **维护成本** | 低（brew 自动管理） |
| **Metal 支持** | ✅ 内置（M1 原生优化） |
| **更新方式** | `brew upgrade whisper-cpp` |
| **路径** | `/opt/homebrew/bin/whisper-cli` |
| **风险** | 极低 |

### 方案 B: 源码编译
```bash
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp && make -j
```
| 维度 | 说明 |
|------|------|
| **安装耗时** | ~10-15 分钟 |
| **维护成本** | 中（需手动更新） |
| **Metal 支持** | ✅ 需确认 `GGML_METAL=1` |
| **更新方式** | `git pull && make clean && make` |
| **路径** | 自定义（如 `~/.openclaw/bin/whisper-cli`） |
| **风险** | 低（编译可能失败） |

**推荐**: 方案 A（brew 安装）— 更快、更稳定、易维护

---

## 📦 模型选择建议

### 可用模型 (GGML 格式)
| 模型 | 大小 | 转写速度 (M1) | 准确率 | 推荐场景 |
|------|------|---------------|--------|----------|
| `tiny` | ~75 MB | ~300x | 低 | 测试/极短音频 |
| `base` | ~142 MB | ~150x | 中 | 快速测试 |
| `small` | ~466 MB | ~60x | 中高 | 日常使用 |
| `medium` | ~1.5 GB | ~20x | 高 | ⭐ **推荐平衡点** |
| `large-v3` | ~3.1 GB | ~10x | 极高 | 高要求场景 |
| `large-v3-turbo` | ~1.6 GB | ~15x | 高 | ⭐ **推荐（速度/质量平衡）** |

### 模型下载路径
- HuggingFace: https://huggingface.co/ggerganov/whisper.cpp/tree/main
- 官方镜像: https://ggml.ggerganov.com/

**推荐模型**: `ggml-large-v3-turbo.bin` (约 1.6GB)
- 理由：在 M1 上速度与质量的最佳平衡点
- 备选：`ggml-medium.bin` (约 1.5GB) 如果追求更小体积

---

## 🗂️ 路径规划

| 类型 | 路径 | 说明 |
|------|------|------|
| **脚本目录** | `/Users/fx/.openclaw/workspace/scripts/` | 已存在，存放 transcribe 脚本 |
| **模型目录** | `/Users/fx/.openclaw/models/whispercpp/` | 需创建，存放 GGML 模型文件 |
| **二进制路径** | `/opt/homebrew/bin/whisper-cli` | brew 安装后的可执行文件 |
| **缓存目录** | `/Users/fx/.openclaw/cache/whisper/` | 可选，用于临时文件 |

---

## 🔧 实施步骤清单

### 阶段 1: 环境准备 (预计 5 分钟)
```bash
# 1. 创建模型目录
mkdir -p /Users/fx/.openclaw/models/whispercpp

# 2. 创建脚本目录（如不存在）
mkdir -p /Users/fx/.openclaw/workspace/scripts

# 3. 验证 brew 状态
brew doctor | head -10
```

### 阶段 2: 安装 whisper.cpp (预计 3 分钟)
```bash
# 安装 whisper-cpp
brew install whisper-cpp

# 验证安装
whisper-cli --version
which whisper-cli
```

### 阶段 3: 下载模型 (预计 10-20 分钟，取决于网络)
```bash
# 进入模型目录
cd /Users/fx/.openclaw/models/whispercpp

# 下载推荐模型 (large-v3-turbo)
curl -L -o ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin

# 验证下载
ls -lh ggml-large-v3-turbo.bin
# 应显示约 1.6G
```

### 阶段 4: 创建转写脚本 (预计 5 分钟)
```bash
# 创建脚本文件
cat > /Users/fx/.openclaw/workspace/scripts/whisper-transcribe << 'EOF'
#!/bin/bash
# whisper.cpp transcribe script for OpenClaw (Metal optimized)

AUDIO_FILE="$1"
shift

# 默认参数
LANGUAGE="zh"
MODEL_PATH="/Users/fx/.openclaw/models/whispercpp/ggml-large-v3-turbo.bin"
TEMPERATURE="0.0"
INITIAL_PROMPT="以下为普通话语音，请输出简体中文原文，不要翻译成英文。"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--language)
            LANGUAGE="$2"
            shift 2
            ;;
        -m|--model)
            MODEL_PATH="$2"
            shift 2
            ;;
        --temperature)
            TEMPERATURE="$2"
            shift 2
            ;;
        --initial-prompt)
            INITIAL_PROMPT="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# 执行转写 (Metal 加速)
whisper-cli \
  -m "$MODEL_PATH" \
  -f "$AUDIO_FILE" \
  -l "$LANGUAGE" \
  --temperature "$TEMPERATURE" \
  --prompt "$INITIAL_PROMPT" \
  -otxt \
  -of /dev/stdout \
  2>/dev/null

echo  # 确保换行
EOF

# 赋予执行权限
chmod +x /Users/fx/.openclaw/workspace/scripts/whisper-transcribe

# 测试脚本（可选）
# /Users/fx/.openclaw/workspace/scripts/whisper-transcribe /path/to/test.wav -l zh
```

### 阶段 5: 更新 OpenClaw 配置 (需用户确认) ⚠️
修改 `/Users/fx/.openclaw/openclaw.json` 中的 `tools.media.audio.models` 部分：

**当前配置** (faster-whisper):
```json
{
  "tools": {
    "media": {
      "audio": {
        "models": [
          {
            "type": "cli",
            "command": "/Users/fx/.agents/skills/faster-whisper/scripts/transcribe",
            "args": [
              "{{MediaPath}}",
              "-l", "zh",
              "-m", "large-v3-turbo",
              "--temperature", "0.0",
              "--initial-prompt", "以下为普通话语音，请输出简体中文原文，不要翻译成英文。"
            ],
            "timeoutSeconds": 90
          }
        ]
      }
    }
  }
}
```

**新配置** (whisper.cpp + Metal):
```json
{
  "tools": {
    "media": {
      "audio": {
        "models": [
          {
            "type": "cli",
            "command": "/Users/fx/.openclaw/workspace/scripts/whisper-transcribe",
            "args": [
              "{{MediaPath}}",
              "-l", "zh",
              "-m", "/Users/fx/.openclaw/models/whispercpp/ggml-large-v3-turbo.bin",
              "--temperature", "0.0",
              "--initial-prompt", "以下为普通话语音，请输出简体中文原文，不要翻译成英文。"
            ],
            "timeoutSeconds": 120
          }
        ]
      }
    }
  }
}
```

**变更点**:
- `command`: 从 faster-whisper 脚本改为 whisper.cpp 脚本
- `args[3]`: 从模型名称改为模型文件绝对路径
- `timeoutSeconds`: 从 90 秒增加到 120 秒（预留缓冲）

### 阶段 6: 验证与回滚 (预计 5 分钟)
```bash
# 验证配置语法
openclaw doctor

# 测试转写（发送一条语音消息到 Telegram）
# 观察日志：openclaw logs | grep -i whisper

# 回滚方式（如有问题）
# 1. 恢复 openclaw.json.bak
cp /Users/fx/.openclaw/openclaw.json.bak /Users/fx/.openclaw/openclaw.json

# 2. 或手动还原 tools.media.audio 部分
```

---

## ⏱️ 预计耗时分解

| 阶段 | 任务 | 预计耗时 | 累计进度 |
|------|------|----------|----------|
| 1 | 环境准备 | 5 分钟 | 25% 🟡 |
| 2 | 安装 whisper.cpp | 3 分钟 | 40% |
| 3 | 下载模型 | 10-20 分钟 | 65% |
| 4 | 创建转写脚本 | 5 分钟 | 80% |
| 5 | 更新配置 + 验证 | 5 分钟 | 100% |
| **总计** | | **28-38 分钟** | |

---

## ⚠️ 风险点与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 模型下载失败/慢 | 中 | 中 | 使用镜像源 / 备用模型 (medium) |
| Metal 加速未生效 | 低 | 低 | 检查 `whisper-cli -h` 确认 Metal 支持 |
| 转写超时 | 中 | 中 | 增加 `timeoutSeconds` 到 180 |
| 中文识别不准 | 低 | 中 | 调整 `--initial-prompt` 或换 `large-v3` |
| 配置语法错误 | 低 | 高 | 先用 `openclaw doctor` 验证 |
| 磁盘空间不足 | 低 | 高 | 检查 `df -h`，确保 >5GB 可用 |

---

## 🔄 回滚方案

### 快速回滚（配置层面）
```bash
# 恢复备份配置
cp /Users/fx/.openclaw/openclaw.json.bak /Users/fx/.openclaw/openclaw.json

# 重启 OpenClaw Gateway
openclaw gateway restart
```

### 完整回滚（卸载 whisper.cpp）
```bash
# 卸载 whisper-cpp
brew uninstall whisper-cpp

# 清理模型文件
rm -rf /Users/fx/.openclaw/models/whispercpp

# 清理脚本
rm /Users/fx/.openclaw/workspace/scripts/whisper-transcribe

# 恢复原配置
cp /Users/fx/.openclaw/openclaw.json.pre-whisper-cli-fix.bak /Users/fx/.openclaw/openclaw.json
```

---

## ✅ 需要用户二次确认的配置修改点

**请确认以下配置变更** (修改 `/Users/fx/.openclaw/openclaw.json`):

```json
// tools.media.audio.models[0].command
"command": "/Users/fx/.openclaw/workspace/scripts/whisper-transcribe"

// tools.media.audio.models[0].args
"args": [
  "{{MediaPath}}",
  "-l", "zh",
  "-m", "/Users/fx/.openclaw/models/whispercpp/ggml-large-v3-turbo.bin",
  "--temperature", "0.0",
  "--initial-prompt", "以下为普通话语音，请输出简体中文原文，不要翻译成英文。"
]

// tools.media.audio.models[0].timeoutSeconds
"timeoutSeconds": 120
```

**确认回复**: "确认执行" 或 "需要调整：[具体修改]"

---

## 📊 进度里程碑

- [x] **25%** - 实施计划产出完成（当前）
- [ ] **50%** - 环境准备 + whisper.cpp 安装完成
- [ ] **75%** - 模型下载 + 脚本创建完成
- [ ] **100%** - 配置更新 + 验证通过

---

**下一步**: 等待用户确认后，开始执行阶段 1-6。
