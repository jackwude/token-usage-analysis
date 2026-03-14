# Bailian Usage 统计问题修复方案

## 问题描述

Bailian (阿里云百炼) API 确实返回完整的 Token 用量数据：
```json
{
  "usage": {
    "prompt_tokens": 14,
    "completion_tokens": 388,
    "total_tokens": 402
  }
}
```

但 OpenClaw 保存到 session 文件中的 usage 全是 0：
```json
{
  "usage": {
    "input": 0,
    "output": 0,
    "cacheRead": 0,
    "cacheWrite": 0,
    "totalTokens": 0
  }
}
```

## 根本原因

问题出在 **pi-agent-core** 库，它没有正确提取 Bailian API 响应中的 usage 字段。

OpenClaw 使用 `api: "openai-completions"` 调用 Bailian API，但 pi-agent-core 可能：
1. 没有正确处理 Bailian 的 usage 字段名 (`prompt_tokens`/`completion_tokens`)
2. 或者在某个环节丢失了 usage 数据

## 解决方案

### 方案 A：修复 OpenClaw/pi-agent-core（长期方案）

向 OpenClaw 提交 Issue，修复 pi-agent-core 的 Bailian usage 提取逻辑。

**Issue 内容**：
- Bailian API 返回 `prompt_tokens`/`completion_tokens`/`total_tokens`
- OpenClaw 的 `normalizeUsage` 函数支持这些字段
- 但 session 文件中 usage 全是 0
- 需要检查 pi-agent-core 的 OpenAI 兼容 API 处理逻辑

### 方案 B：Collector 直接调用 Bailian API 统计（临时方案）

修改 `collector.py`，对于 Bailian 模型的 session：
1. 不依赖 session 文件中的 usage
2. 直接用 tiktoken 估算 Token 用量
3. 或者调用 Bailian API 查询用量（如果有 API）

## 实施计划

1. **立即**：修改 collector.py 添加 tiktoken 估算支持
2. **短期**：向 OpenClaw 提交 Issue
3. **长期**：等待 OpenClaw 修复后移除 tiktoken 估算

## Bailian 定价参考

| 模型 | Input 价格 | Output 价格 |
|------|-----------|-----------|
| qwen3.5-plus | ¥0.004/1K tokens | ¥0.012/1K tokens |
| qwen3-max | ¥0.02/1K tokens | ¥0.06/1K tokens |
| qwen-plus | ¥0.002/1K tokens | ¥0.006/1K tokens |

## 测试验证

```bash
# 测试 Bailian API 返回 usage
curl -X POST "https://coding.dashscope.aliyuncs.com/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.5-plus","messages":[{"role":"user","content":"你好"}]}'

# 预期输出包含 usage 字段
```
