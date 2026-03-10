# 方案 B（whisper.cpp + Metal）完整改造计划 v2

**创建时间**: 2026-03-07 20:11  
**目标**: 将音频转写引擎从 faster-whisper 迁移至 whisper.cpp（brew 安装，Metal 加速）  
**约束**: 不执行改动，仅产出计划

---

## 一、分阶段步骤

### 阶段 1：准备（Pre-flight）
**预计耗时**: 2-3 分钟

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1.1 | 检查当前 openclaw.json 备份 | `cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup.$(date +%Y%m%d-%H%M%S)` |
| 1.2 | 检查现有 whisper 相关进程 | `ps aux | grep whisper` 确认无冲突 |
| 1.3 | 检查磁盘空间 | `df -h ~/.openclaw` 确保有 ≥5GB 可用（模型约 3GB） |
| 1.4 | 创建目标目录 | `mkdir -p ~/.openclaw/bin ~/.openclaw/models/whispercpp` |

**进度里程碑**: ✅ 25% 完成（准备就绪）

---

### 阶段 2：安装 whisper.cpp（brew）
**预计耗时**: 3-5 分钟

| 步骤 | 操作 | 说明 |
|------|------|------|
| 2.1 | 检查 Homebrew 状态 | `brew --version` 确认 brew 可用 |
| 2.2 | 搜索 whisper 相关包 | `brew search whisper` 确认包名 |
| 2.3 | 安装 whisper-cpp | `brew install whisper-cpp` 核心库（含 Metal 支持） |
| 2.4 | 验证安装 | `whisper-cli --version` 或 `which whisper-cli` |

**注意**: whisper-cpp 的 brew 包通常包含 `whisper-cli` 命令行工具，无需单独安装。

**进度里程碑**: ✅ 50% 完成（工具链就绪）

---

### 阶段 3：下载模型（ggml-large-v3.bin）
**预计耗时**: 10-20 分钟（取决于网络）

| 步骤 | 操作 | 说明 |
|------|------|------|
| 3.1 | 确认模型 URL | 使用 whisper.cpp 官方 HuggingFace 仓库 |
| 3.2 | 下载模型 | `curl -L -o ~/.openclaw/models/whispercpp/ggml-large-v3.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin` |
| 3.3 | 校验完整性 | `shasum -a 256 ~/.openclaw/models/whispercpp/ggml-large-v3.bin` 对比官方 SHA |
| 3.4 | 记录模型大小 | `ls -lh ~/.openclaw/models/whispercpp/ggml-large-v3.bin` 预期约 3GB |

**模型信息**:
- 文件名: `ggml-large-v3.bin`
- 大小: ~3.09 GB
- 语言支持: 多语言（含中文）
- 精度: FP16

**进度里程碑**: ✅ 75% 完成（模型就绪）

---

### 阶段 4：创建转写脚本
**预计耗时**: 5 分钟

| 步骤 | 操作 | 说明 |
|------|------|------|
| 4.1 | 创建脚本文件 | `cat > ~/.openclaw/bin/whisper-transcribe << 'EOF'` |
| 4.2 | 编写脚本内容 | 见下方脚本模板 |
| 4.3 | 赋予执行权限 | `chmod +x ~/.openclaw/bin/whisper-transcribe` |
| 4.4 | 测试脚本 | `~/.openclaw/bin/whisper-transcribe /path/to/test.wav` |

**脚本模板** (`~/.openclaw/bin/whisper-transcribe`):
```bash
#!/bin/bash
# whisper.cpp 转写脚本（Metal 加速）
# 用法：whisper-transcribe <音频文件路径> [语言]

MEDIA_PATH="$1"
LANGUAGE="${2:-zh}"
MODEL_PATH="$HOME/.openclaw/models/whispercpp/ggml-large-v3.bin"

if [ ! -f "$MEDIA_PATH" ]; then
    echo "错误：文件不存在 $MEDIA_PATH" >&2
    exit 1
fi

if [ ! -f "$MODEL_PATH" ]; then
    echo "错误：模型不存在 $MODEL_PATH" >&2
    exit 1
fi

# 执行转写（whisper-cli 自动使用 Metal 加速）
whisper-cli \
    -m "$MODEL_PATH" \
    -f "$MEDIA_PATH" \
    -l "$LANGUAGE" \
    --temperature 0.0 \
    --prompt "以下为普通话语音，请输出简体中文原文，不要翻译成英文。" \
    --no-timestamps \
    --output-json 2>/dev/null | \
    jq -r '.text // empty' 2>/dev/null || \
whisper-cli \
    -m "$MODEL_PATH" \
    -f "$MEDIA_PATH" \
    -l "$LANGUAGE" \
    --temperature 0.0 \
    --prompt "以下为普通话语音，请输出简体中文原文，不要翻译成英文。" \
    --no-timestamps
```

**进度里程碑**: ✅ 85% 完成（脚本就绪）

---

### 阶段 5：配置 openclaw.json
**预计耗时**: 2 分钟  
**⚠️ 需要两次确认**

| 步骤 | 操作 | 说明 |
|------|------|------|
| 5.1 | **第一次确认** | 向用户展示拟修改的字段，等待确认 |
| 5.2 | 备份配置 | `cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.pre-whispercpp` |
| 5.3 | 修改配置 | 编辑 `tools.media.audio.models[0]`（见下方确切字段） |
| 5.4 | **第二次确认** | 向用户展示修改后的配置，等待确认后保存 |
| 5.5 | 验证 JSON 语法 | `cat ~/.openclaw/openclaw.json | jq . >/dev/null` |

**需要修改的确切字段**:

```json
// 原配置（faster-whisper）：
"tools": {
  "media": {
    "audio": {
      "enabled": true,
      "maxBytes": 20971520,
      "maxChars": 6000,
      "models": [
        {
          "type": "cli",
          "command": "/Users/fx/.agents/skills/faster-whisper/scripts/transcribe",
          "args": [
            "{{MediaPath}}",
            "-l",
            "zh",
            "-m",
            "large-v3-turbo",
            "--temperature",
            "0.0",
            "--initial-prompt",
            "以下为普通话语音，请输出简体中文原文，不要翻译成英文。"
          ],
          "timeoutSeconds": 90
        }
      ]
    }
  }
}

// ↓ 修改为 ↓（whisper.cpp）：

"tools": {
  "media": {
    "audio": {
      "enabled": true,
      "maxBytes": 20971520,
      "maxChars": 6000,
      "models": [
        {
          "type": "cli",
          "command": "/Users/fx/.openclaw/bin/whisper-transcribe",
          "args": [
            "{{MediaPath}}",
            "zh"
          ],
          "timeoutSeconds": 120
        }
      ]
    }
  }
}
```

**修改说明**:
- `command`: 改为新脚本路径 `/Users/fx/.openclaw/bin/whisper-transcribe`
- `args`: 简化为仅传递 `{{MediaPath}}` 和语言 `zh`（脚本内部处理模型路径和提示词）
- `timeoutSeconds`: 从 90 增至 120（whisper.cpp 可能稍慢但更准确）

**进度里程碑**: ✅ 95% 完成（配置就绪）

---

### 阶段 6：验证
**预计耗时**: 5 分钟

| 步骤 | 操作 | 说明 |
|------|------|------|
| 6.1 | 准备测试音频 | 使用一段已知内容的中文语音（30 秒以内） |
| 6.2 | 手动测试脚本 | `~/.openclaw/bin/whisper-transcribe /path/to/test.wav zh` |
| 6.3 | 检查输出 | 确认识别结果准确，无乱码 |
| 6.4 | 测试 OpenClaw 集成 | 发送一段语音消息到 Telegram，观察转写结果 |
| 6.5 | 性能基准 | 记录转写耗时（预期：30 秒音频 ≈ 10-20 秒处理） |

**进度里程碑**: ✅ 100% 完成（验证通过）

---

### 阶段 7：回滚方案（仅在需要时执行）
**预计耗时**: 2-5 分钟

见下方"回滚方案"章节。

---

## 二、为什么通过 agents.defaults 继承？

**当前配置位置**: `agents.defaults` 是所有 Agent 的默认配置模板。

**原因**:
1. **统一性**: 所有 Agent（main、tg-office 及未来新增）自动继承相同的音频转写配置
2. **维护性**: 只需修改一处，无需逐个 Agent 更新
3. **一致性**: 避免不同 Agent 使用不同转写引擎导致的行为差异
4. **扩展性**: 未来新增 Agent 自动获得音频处理能力

**配置继承链**:
```
agents.defaults.tools.media.audio.models[0]
    ↓ 继承
agent:main
    ↓ 继承
agent:tg-office
    ↓ 继承
未来所有新 Agent
```

**注意**: 当前 openclaw.json 中 `tools` 是全局配置（非 agents 下），修改后对所有 Agent 生效。

---

## 三、风险点清单 + 对策

| 风险编号 | 风险描述 | 概率 | 影响 | 对策 |
|----------|----------|------|------|------|
| R1 | brew 安装失败（网络/依赖冲突） | 中 | 中 | 先 `brew update`；失败则手动从 GitHub 下载 whisper.cpp 源码编译 |
| R2 | 模型下载失败或损坏 | 中 | 高 | 使用 curl -L 强制跟随重定向；下载后校验 SHA256；准备备用下载源 |
| R3 | Metal 加速未生效（退化为 CPU） | 低 | 中 | 运行 `whisper-cli -m <model> -f <audio> --print-progress` 观察是否有 "metal" 字样；如退化，检查 macOS 版本和 GPU 驱动 |
| R4 | 转写结果乱码或语言识别错误 | 低 | 中 | 脚本中硬编码 `-l zh`；使用 `--prompt` 强制中文输出；测试阶段用已知内容验证 |
| R5 | openclaw.json 语法错误导致服务无法启动 | 低 | 高 | 修改前备份；修改后用 `jq` 验证；保留回滚方案 |
| R6 | 脚本权限不足无法执行 | 低 | 中 | `chmod +x` 后测试；检查 shebang 行是否正确 |
| R7 | 磁盘空间不足（模型 3GB） | 低 | 中 | 阶段 1.3 检查；不足则清理或扩展 |
| R8 | whisper-cli 参数与预期不符 | 中 | 中 | 安装后先 `whisper-cli --help` 确认参数；脚本增加容错逻辑 |

---

## 四、回滚方案

### 4.1 配置回滚（快速）

```bash
# 恢复备份的配置
cp ~/.openclaw/openclaw.json.pre-whispercpp ~/.openclaw/openclaw.json

# 验证 JSON 语法
cat ~/.openclaw/openclaw.json | jq . >/dev/null && echo "✓ 配置回滚成功"

# 重启 OpenClaw Gateway（如需要）
openclaw gateway restart
```

**前提**: 阶段 5.2 已创建备份 `~/.openclaw/openclaw.json.pre-whispercpp`

---

### 4.2 文件清理回滚（需用户二次确认）

**⚠️ 以下操作需要用户明确点名路径后执行**

| 文件/目录 | 路径 | 说明 |
|-----------|------|------|
| 转写脚本 | `/Users/fx/.openclaw/bin/whisper-transcribe` | 阶段 4 创建 |
| 模型文件 | `/Users/fx/.openclaw/models/whispercpp/ggml-large-v3.bin` | 阶段 3 下载（约 3GB） |
| 模型目录 | `/Users/fx/.openclaw/models/whispercpp/` | 如确认不再使用 whisper.cpp 可删除 |

**清理命令**（需用户确认后执行）:
```bash
# 用户确认后执行：
rm /Users/fx/.openclaw/bin/whisper-transcribe
rm /Users/fx/.openclaw/models/whispercpp/ggml-large-v3.bin
rmdir /Users/fx/.openclaw/models/whispercpp 2>/dev/null || true
```

**注意**: 
- 模型文件较大（3GB），删除前务必确认
- 如用户计划未来使用 whisper.cpp，建议保留模型，仅回滚配置

---

### 4.3 brew 卸载（可选）

```bash
# 如确认不再需要 whisper.cpp
brew uninstall whisper-cpp
```

**建议**: 保留 brew 包，仅回滚配置和删除模型，以便未来快速恢复。

---

## 五、执行检查清单（Checklist）

执行前逐项确认：

- [ ] 阶段 1: 备份完成，磁盘空间充足
- [ ] 阶段 2: whisper-cli 安装成功，`which whisper-cli` 有输出
- [ ] 阶段 3: 模型下载完成，SHA256 校验通过
- [ ] 阶段 4: 脚本创建成功，`chmod +x` 已执行
- [ ] 阶段 5: **第一次确认** 已完成（用户同意修改配置）
- [ ] 阶段 5: 配置备份完成
- [ ] 阶段 5: **第二次确认** 已完成（用户确认配置内容）
- [ ] 阶段 6: 手动测试脚本通过
- [ ] 阶段 6: OpenClaw 集成测试通过

---

## 六、预计总耗时

| 阶段 | 预计耗时 |
|------|----------|
| 准备 | 2-3 分钟 |
| 安装 | 3-5 分钟 |
| 下载模型 | 10-20 分钟 |
| 脚本创建 | 5 分钟 |
| 配置修改 | 2 分钟（不含等待确认时间） |
| 验证 | 5 分钟 |
| **总计** | **27-40 分钟** |

**关键路径**: 模型下载（10-20 分钟）是主要耗时环节。

---

## 七、后续优化建议（可选）

1. **模型量化**: 如需节省空间，可下载 `ggml-large-v3-q5_0.bin`（约 1.1GB，精度损失小）
2. **并行处理**: whisper.cpp 支持批处理，可优化多音频队列
3. **缓存机制**: 对相同音频哈希缓存转写结果，避免重复计算
4. **监控告警**: 增加转写失败率和延迟监控

---

**文档结束**  
**下次更新**: 执行后根据实际经验更新风险点和耗时估算
