#!/bin/bash

API_KEY="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"
API_URL="https://integrate.api.nvidia.com/v1/chat/completions"

MODELS=(
    "mistralai/mistral-large-2-instruct"
    "meta/llama-4-maverick-17b-128e-instruct"
    "meta/llama-4-scout-17b-16e-instruct"
    "mistralai/mistral-small-3.1-24b-instruct-2503"
    "qwen/qwen3.5-122b-a10b"
)

echo "============================================"
echo "NVIDIA 模型连通性与并行工具调用测试"
echo "============================================"
echo ""

# 结果数组
declare -a RESULTS

for MODEL in "${MODELS[@]}"; do
    echo "测试模型：$MODEL"
    echo "-------------------------------------------"
    
    # 测试 1：基础连通性
    START_TIME=$(date +%s)
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$MODEL\",
            \"messages\": [{\"role\": \"user\", \"content\": \"Hello, please respond with just 'OK'\"}],
            \"max_tokens\": 10
        }")
    END_TIME=$(date +%s)
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')
    RESPONSE_TIME=$(( (END_TIME - START_TIME) * 1000 ))
    
    if [ "$HTTP_CODE" = "200" ]; then
        CONNECTIVITY="✅"
        echo "  连通性：✅ 成功 (${RESPONSE_TIME}ms)"
    else
        CONNECTIVITY="❌"
        echo "  连通性：❌ 失败 (HTTP $HTTP_CODE, ${RESPONSE_TIME}ms)"
        echo "  错误：$RESPONSE_BODY"
    fi
    
    # 测试 2：并行工具调用支持
    TOOL_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$MODEL\",
            \"messages\": [{\"role\": \"user\", \"content\": \"What's the weather and time?\"}],
            \"tools\": [
                {
                    \"type\": \"function\",
                    \"function\": {
                        \"name\": \"get_weather\",
                        \"description\": \"Get current weather\",
                        \"parameters\": {
                            \"type\": \"object\",
                            \"properties\": {
                                \"location\": {\"type\": \"string\", \"description\": \"City name\"}
                            },
                            \"required\": [\"location\"]
                        }
                    }
                },
                {
                    \"type\": \"function\",
                    \"function\": {
                        \"name\": \"get_time\",
                        \"description\": \"Get current time\",
                        \"parameters\": {
                            \"type\": \"object\",
                            \"properties\": {
                                \"timezone\": {\"type\": \"string\", \"description\": \"Timezone\"}
                            },
                            \"required\": [\"timezone\"]
                        }
                    }
                }
            ],
            \"tool_choice\": \"auto\"
        }")
    
    TOOL_HTTP_CODE=$(echo "$TOOL_RESPONSE" | tail -n1)
    TOOL_RESPONSE_BODY=$(echo "$TOOL_RESPONSE" | sed '$d')
    
    if [ "$TOOL_HTTP_CODE" = "200" ]; then
        PARALLEL_SUPPORT="✅"
        echo "  并行工具调用：✅ 支持"
    elif [ "$TOOL_HTTP_CODE" = "400" ]; then
        if echo "$TOOL_RESPONSE_BODY" | grep -qi "single tool-calls\|parallel\|only one tool"; then
            PARALLEL_SUPPORT="❌"
            echo "  并行工具调用：❌ 不支持 (仅支持单个工具调用)"
        else
            PARALLEL_SUPPORT="❌"
            echo "  并行工具调用：❌ 错误 (HTTP 400)"
            echo "  错误详情：$TOOL_RESPONSE_BODY"
        fi
    else
        PARALLEL_SUPPORT="❌"
        echo "  并行工具调用：❌ 错误 (HTTP $TOOL_HTTP_CODE)"
    fi
    
    # 存储结果
    RESULTS+=("$MODEL|$CONNECTIVITY|$RESPONSE_TIME|$PARALLEL_SUPPORT")
    
    echo ""
done

# 输出汇总表格
echo "============================================"
echo "测试结果汇总"
echo "============================================"
echo ""
printf "| %-45s | %-8s | %-10s | %-12s |\n" "模型" "连通性" "响应时间" "并行工具调用"
echo "|----------------------------------------------|----------|------------|--------------|"

for RESULT in "${RESULTS[@]}"; do
    IFS='|' read -r MODEL CONNECTIVITY RESPONSE_TIME PARALLEL_SUPPORT <<< "$RESULT"
    # 截断模型名称以适应表格
    SHORT_MODEL=$(echo "$MODEL" | cut -c1-43)
    printf "| %-45s | %-8s | %-10s | %-12s |\n" "$SHORT_MODEL" "$CONNECTIVITY" "${RESPONSE_TIME}ms" "$PARALLEL_SUPPORT"
done

echo ""
echo "============================================"
echo "汇总建议"
echo "============================================"
echo ""

# 统计可用的模型
RECOMMENDED=()
for RESULT in "${RESULTS[@]}"; do
    IFS='|' read -r MODEL CONNECTIVITY RESPONSE_TIME PARALLEL_SUPPORT <<< "$RESULT"
    if [ "$CONNECTIVITY" = "✅" ]; then
        if [ "$PARALLEL_SUPPORT" = "✅" ]; then
            RECOMMENDED+=("⭐ $MODEL (连通性✅ + 并行工具✅)")
        else
            RECOMMENDED+=("✓ $MODEL (连通性✅ + 并行工具❌)")
        fi
    fi
done

if [ ${#RECOMMENDED[@]} -gt 0 ]; then
    echo "推荐添加到 OpenClaw 配置的模型："
    for REC in "${RECOMMENDED[@]}"; do
        echo "  $REC"
    done
else
    echo "⚠️ 没有模型通过基础连通性测试，建议检查 API_KEY 或网络配置"
fi

echo ""
echo "测试完成时间：$(date '+%Y-%m-%d %H:%M:%S')"
