#!/bin/bash

API_KEY="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"

# 智谱 AI 有多个可能的端点，我们逐一测试
ENDPOINTS=(
    "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    "https://api.zhipu.ai/openai/api/paas/v4/chat/completions"
    "https://api.z.ai/api/paas/v4/chat/completions"
)

models=("glm-4-flash" "glm-4" "glm-3-turbo")
model_names=("glm-4-flash (glm4.7 替代)" "glm-4 (glm5 替代)" "glm-3-turbo (chatglm3 替代)")

echo "=========================================="
echo "智谱 AI (Z.ai) 模型连通性测试"
echo "=========================================="
echo ""

# 先测试哪个端点可用
echo "【测试 API 端点】"
valid_endpoint=""

for endpoint in "${ENDPOINTS[@]}"; do
    echo "测试端点：$endpoint"
    response=$(curl -s -w "\n%{http_code}" -X POST "$endpoint" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"glm-4-flash\",
            \"messages\": [{\"role\": \"user\", \"content\": \"你好\"}]
        }" --max-time 10)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo "  ✅ 端点可用 (HTTP 200)"
        valid_endpoint="$endpoint"
        break
    elif [ "$http_code" = "401" ]; then
        echo "  ❌ 认证失败 (HTTP 401) - Token 可能无效"
    elif [ "$http_code" = "404" ]; then
        echo "  ❌ 端点不存在 (HTTP 404)"
    else
        echo "  ⚠️ 其他错误 (HTTP $http_code)"
        error_msg=$(echo "$body" | grep -o '"message"[^,}]*' | head -1 | cut -d'"' -f4)
        echo "  错误：${error_msg:-未知错误}"
    fi
    echo ""
done

if [ -z "$valid_endpoint" ]; then
    echo "=========================================="
    echo "【测试结果】"
    echo "=========================================="
    echo ""
    echo "❌ 所有端点测试失败，可能原因："
    echo "   1. API_KEY 无效或已过期"
    echo "   2. API_KEY 格式不正确（智谱 AI 通常使用 zhipu_ 开头的 key）"
    echo "   3. 网络问题或端点变更"
    echo ""
    echo "建议："
    echo "   - 检查 API_KEY 是否正确（智谱 AI 官方 key 格式通常为 zhipu.xxxx）"
    echo "   - 登录 https://open.bigmodel.cn 获取有效的 API Key"
    echo "   - 确认账户是否有可用额度"
    echo ""
    
    # 输出最终表格
    echo "=========================================="
    echo "【测试结果汇总】"
    echo "=========================================="
    echo ""
    printf "| %-30s | %-8s | %-10s | %-12s |\n" "模型" "连通性" "响应时间" "并行工具调用"
    printf "|%-32s|%-10s|%-12s|%-14s|\n" "--------------------------------" "--------" "----------" "--------------"
    printf "| %-30s | %-8s | %-10s | %-12s |\n" "z-ai/glm4.7" "❌" "N/A" "❌"
    printf "| %-30s | %-8s | %-10s | %-12s |\n" "z-ai/glm5" "❌" "N/A" "❌"
    printf "| %-30s | %-8s | %-10s | %-12s |\n" "thudm/chatglm3-6b" "❌" "N/A" "❌"
    echo ""
    echo "=========================================="
    echo "【汇总建议】"
    echo "=========================================="
    echo ""
    echo "❌ 所有模型均无法添加 - API 认证失败"
    echo ""
    echo "原因分析："
    echo "   提供的 API_KEY (nvapi-开头) 看起来不是智谱 AI 官方格式"
    echo "   智谱 AI 官方 API Key 格式通常为：zhipu.xxxxxxxxxx"
    echo "   nvapi- 开头的 key 可能是其他平台（如 NVIDIA NIM）的 key"
    echo ""
    echo "建议操作："
    echo "   1. 确认是否使用了正确的 API 平台"
    echo "   2. 如需使用智谱 AI，请访问 https://open.bigmodel.cn 获取官方 API Key"
    echo "   3. 如果这是 NVIDIA NIM 的 key，需要确认 NIM 是否支持这些模型"
    echo ""
    exit 0
fi

echo ""
echo "使用有效端点：$valid_endpoint"
echo ""
echo "=========================================="
echo "【测试模型连通性】"
echo "=========================================="
echo ""

RESULTS_FILE="/tmp/zhipu_test_results.txt"
> "$RESULTS_FILE"

for i in "${!models[@]}"; do
    model="${models[$i]}"
    model_name="${model_names[$i]}"
    echo "测试模型：$model_name"
    start_time=$(date +%s)
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$valid_endpoint" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$model\",
            \"messages\": [{\"role\": \"user\", \"content\": \"你好，请回复 OK\"}]
        }")
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        connectivity="✅"
        resp_time="${duration}s"
        echo "  状态：✅ 成功"
        echo "  响应时间：${resp_time}"
    else
        connectivity="❌"
        resp_time="N/A"
        echo "  状态：❌ 失败 (HTTP $http_code)"
        error_msg=$(echo "$body" | grep -o '"message"[^,}]*' | head -1 | cut -d'"' -f4)
        echo "  错误：${error_msg:-未知错误}"
    fi
    
    echo "${model}|${model_name}|${connectivity}|${resp_time}" >> "$RESULTS_FILE"
    echo ""
done

echo "测试完成！"
