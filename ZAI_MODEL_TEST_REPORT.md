# Z.ai (智谱 AI) 模型连通性测试报告

**测试日期**: 2026-03-15  
**API_KEY**: `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` (NVIDIA NIM)  
**测试平台**: NVIDIA NIM API (`https://integrate.api.nvidia.com/v1`)

---

## 测试结果汇总

| 模型 | 连通性 | 响应时间 | 并行工具调用 |
|------|--------|----------|-------------|
| z-ai/glm4.7 | ❌ | N/A | ❌ |
| z-ai/glm5 | ❌ | N/A | ❌ |
| thudm/chatglm3-6b | ✅ | ~1.9s | ⚠️ |

---

## 详细测试结果

### 1. z-ai/glm4.7 (glm-4-flash)

- **连通性**: ❌ 失败
- **HTTP 状态码**: 404
- **错误信息**: Model not found
- **原因**: 该模型在 NVIDIA NIM 平台上不存在或名称不正确

### 2. z-ai/glm5 (glm-4)

- **连通性**: ❌ 失败
- **HTTP 状态码**: 404
- **错误信息**: Model not found
- **原因**: 该模型在 NVIDIA NIM 平台上不存在或名称不正确

### 3. thudm/chatglm3-6b

- **连通性**: ✅ 成功
- **响应时间**: ~1.9 秒
- **并行工具调用**: ⚠️ 配置问题
- **错误信息**: `"auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set`
- **分析**: 这是服务端配置问题，不是模型本身不支持工具调用。模型可以正常进行基础对话。

---

## 汇总建议

### ✅ 可以添加的模型

| 模型 | 建议 | 说明 |
|------|------|------|
| `thudm/chatglm3-6b` | **有条件推荐** | 连通性正常，响应时间合理 (~2s)。工具调用功能受限于 NVIDIA NIM 服务端配置，但基础对话功能完全可用。 |

### ❌ 不建议添加的模型

| 模型 | 原因 |
|------|------|
| `z-ai/glm4.7` | 在 NVIDIA NIM 平台上不可用 (404) |
| `z-ai/glm5` | 在 NVIDIA NIM 平台上不可用 (404) |

---

## 重要说明

### API_KEY 格式分析

提供的 API_KEY (`nvapi-` 开头) 是 **NVIDIA NIM** 的格式，不是智谱 AI 官方 (`zhipu.` 开头) 的格式。

- **当前测试平台**: NVIDIA NIM (`https://integrate.api.nvidia.com/v1`)
- **智谱 AI 官方平台**: `https://open.bigmodel.cn/api/paas/v4`

### 如需使用更多智谱 AI 模型

如果需要测试智谱 AI 官方的更多模型（如 glm-4、glm-4-flash 等），建议：

1. 访问 https://open.bigmodel.cn 获取官方 API Key（格式：`zhipu.xxxxxxxxxx`）
2. 使用官方端点：`https://open.bigmodel.cn/api/paas/v4/chat/completions`
3. 重新进行连通性测试

---

## OpenClaw 配置建议

### 推荐添加配置

```json
{
  "model": "thudm/chatglm3-6b",
  "base_url": "https://integrate.api.nvidia.com/v1",
  "api_key": "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",
  "notes": "连通性正常，响应时间~2s。工具调用功能受限于 NIM 服务端配置。"
}
```

### 注意事项

1. **仅基础对话可用**: 当前配置下，`thudm/chatglm3-6b` 仅支持基础对话，工具调用功能需要 NVIDIA NIM 服务端额外配置
2. **响应时间**: 约 1.9 秒，可以接受
3. **模型能力**: ChatGLM3-6B 是较早期的模型，能力相对有限，适合简单对话场景

---

**测试完成时间**: 2026-03-15 14:38 GMT+8
