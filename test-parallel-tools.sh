#!/bin/bash

API_KEY="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"

echo "🔍 开始测试 NVIDIA 模型并行工具调用支持情况..."
echo "================================================"
echo ""

# 测试结果
RESULTS=""

# 测试函数
test_model() {
    local MODEL="$1"
    echo "📌 测试模型：$MODEL"
    
    # 构建包含 2 个工具调用的请求
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://integrate.api.nvidia.com/v1/chat/completions" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$MODEL\",
            \"messages\": [{\"role\": \"user\", \"content\": \"请调用两个工具：1. 查询天气 2. 查询时间\"}],
            \"tools\": [
                {
                    \"type\": \"function\",
                    \"function\": {
                        \"name\": \"get_weather\",
                        \"description\": \"获取天气信息\",
                        \"parameters\": {
                            \"type\": \"object\",
                            \"properties\": {
                                \"location\": {\"type\": \"string\", \"description\": \"城市名\"}
                            },
                            \"required\": [\"location\"]
                        }
                    }
                },
                {
                    \"type\": \"function\",
                    \"function\": {
                        \"name\": \"get_time\",
                        \"description\": \"获取当前时间\",
                        \"parameters\": {
                            \"type\": \"object\",
                            \"properties\": {
                                \"timezone\": {\"type\": \"string\", \"description\": \"时区\"}
                            },
                            \"required\": [\"timezone\"]
                        }
                    }
                }
            ],
            \"tool_choice\": \"auto\"
        }" 2>&1)
    
    # 提取 HTTP 状态码和响应体
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    # 检查响应
    if [[ "$HTTP_CODE" == "200" ]]; then
        echo "   ✅ 支持并行工具调用 (HTTP 200)"
        RESULTS="${RESULTS}${MODEL}|✅ 支持\n"
    elif [[ "$HTTP_CODE" == "400" ]]; then
        # 检查错误信息是否包含 parallel 或 single tool-calls
        if echo "$BODY" | grep -qi "parallel\|single tool-calls\|tool.*call"; then
            echo "   ❌ 不支持并行工具调用 (HTTP 400 - 包含 parallel/single tool-calls 错误)"
            RESULTS="${RESULTS}${MODEL}|❌ 不支持\n"
        else
            echo "   ⚠️  其他错误 (HTTP 400): $(echo "$BODY" | head -c 100)"
            RESULTS="${RESULTS}${MODEL}|⚠️ 其他错误\n"
        fi
    else
        echo "   ⚠️  未知状态 (HTTP $HTTP_CODE)"
        RESULTS="${RESULTS}${MODEL}|⚠️ HTTP $HTTP_CODE\n"
    fi
    
    echo ""
}

# 测试所有模型
test_model "meta/llama-3.2-90b-vision-instruct"
test_model "meta/llama-3.3-70b-instruct"
test_model "minimaxai/minimax-m2.1"
test_model "google/gemma-3-27b-it"
test_model "meta/llama-3.1-405b-instruct"
test_model "minimaxai/minimax-m2.5"

# 输出汇总表格
echo "================================================"
echo "📊 测试结果汇总"
echo "================================================"
echo ""
printf "%-40s | %s\n" "模型" "支持情况"
echo "------------------------------------------------"
echo -e "$RESULTS" | while IFS='|' read -r model status; do
    if [[ -n "$model" ]]; then
        printf "%-40s | %s\n" "$model" "$status"
    fi
done
echo ""
