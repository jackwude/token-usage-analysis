# OpenClaw Issue 草稿

## 提交位置
https://github.com/openclaw/openclaw/issues/new

---

## Title
**Bailian (ModelStudio) provider does not save usage tokens to session files**

## Description

### Problem
Bailian API (阿里云百炼) returns complete usage data in API responses:
```json
{
  "usage": {
    "prompt_tokens": 14,
    "completion_tokens": 388,
    "total_tokens": 402
  }
}
```

However, OpenClaw saves session files with all-zero usage:
```json
{
  "usage": {
    "input": 0,
    "output": 0,
    "totalTokens": 0,
    "cost": {"total": 0}
  }
}
```

### Impact
- Cannot track Token consumption for Bailian models
- Cannot calculate costs for qwen3.5-plus, qwen3-max, glm, kimi models
- Token usage analysis tools show 0 for all Bailian sessions

### Root Cause
The issue appears to be in **pi-agent-core** library:
- OpenClaw uses `api: "openai-completions"` for Bailian
- Bailian API returns `prompt_tokens`/`completion_tokens`/`total_tokens`
- OpenClaw's `normalizeUsage()` function supports these field names
- But the usage data is not being extracted and saved to session files

### Reproduction
1. Configure OpenClaw with Bailian provider (ModelStudio)
2. Run any chat completion with qwen3.5-plus model
3. Check session file in `~/.openclaw/agents/main/sessions/*.jsonl`
4. Observe `usage` field is all zeros

### Expected Behavior
Session files should contain actual usage data:
```json
{
  "usage": {
    "input": 14,
    "output": 388,
    "total": 402
  }
}
```

### Environment
- OpenClaw version: 2026.3.11
- Provider: bailian (ModelStudio)
- Models affected: qwen3.5-plus, qwen3-max-2026-01-23, glm-5, kimi-k2.5, etc.
- API endpoint: https://coding.dashscope.aliyuncs.com/v1

### Additional Context
- Bailian API is OpenAI-compatible and returns standard usage fields
- OpenClaw's `normalizeUsage()` already supports `prompt_tokens`/`completion_tokens`
- The issue is likely in pi-agent-core's response parsing
- This affects cost tracking and usage analytics for Bailian users

### Suggested Fix
Check pi-agent-core's handling of OpenAI-compatible API responses:
1. Ensure `usage` field is extracted from API response
2. Map `prompt_tokens` → `input`, `completion_tokens` → `output`
3. Save normalized usage to session file

---

## 中文版本（可选）

### 问题
Bailian API 返回完整的用量数据，但 OpenClaw 保存到 session 文件的 usage 全是 0。

### 影响
- 无法统计 Bailian 模型的 Token 消耗
- 无法计算成本
- 用量分析工具显示为 0

### 根本原因
pi-agent-core 库没有正确提取 Bailian API 响应中的 usage 字段。

### 建议修复
检查 pi-agent-core 对 OpenAI 兼容 API 响应的处理：
1. 确保从 API 响应中提取 `usage` 字段
2. 映射 `prompt_tokens` → `input`, `completion_tokens` → `output`
3. 保存 normalized usage 到 session 文件

---

## Labels
- `bug`
- `provider:bailian`
- `provider:modelstudio`
- `usage-tracking`
- `pi-agent-core`
