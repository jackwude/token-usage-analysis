#!/bin/bash

API_KEY="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"
BASE_URL="https://api.z.ai/api/paas/v4"

RESULTS_FILE="/tmp/zai_test_results.txt"
> "$RESULTS_FILE"

models=("glm4.7" "glm5" "chatglm3-6b")
model_prefixes=("z-ai/" "z-ai/" "thudm/")

echo "=========================================="
echo "Z.ai 模型连通性与并行工具调用测试"
echo "=========================================="
echo ""

# 测试 1：基础连通性
echo "【测试 1：基础连通性】"
echo ""

for i in "${!models[@]}"; do
    model="${model_prefixes[$i]}${models[$i]}"
    model_short="${models[$i]}"
    echo "测试模型：$model"
    start_time=$(date +%s)
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/chat/completions" \
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
    
    # 保存到文件
    echo "${model_short}|${connectivity}|${resp_time}" >> "$RESULTS_FILE"
    echo ""
done

# 测试 2：并行工具调用支持
echo "【测试 2：并行工具调用支持】"
echo ""

# 清空文件重新记录
> "$RESULTS_FILE"

for i in "${!models[@]}"; do
    model="${model_prefixes[$i]}${models[$i]}"
    model_short="${models[$i]}"
    echo "测试模型：$model"
    
    # 先获取连通性结果
    start_time=$(date +%s)
    conn_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/chat/completions" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$model\",
            \"messages\": [{\"role\": \"user\", \"content\": \"你好\"}]
        }")
    end_time=$(date +%s)
    conn_duration=$((end_time - start_time))
    conn_code=$(echo "$conn_response" | tail -n1)
    
    if [ "$conn_code" = "200" ]; then
        connectivity="✅"
        resp_time="${conn_duration}s"
    else
        connectivity="❌"
        resp_time="N/A"
    fi
    
    # 测试并行工具调用
    tool_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/chat/completions" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$model\",
            \"messages\": [{\"role\": \"user\", \"content\": \"请帮我查询天气和新闻\"}],
            \"tools\": [
                {
                    \"type\": \"function\",
                    \"function\": {
                        \"name\": \"get_weather\",
                        \"description\": \"获取天气信息\",
                        \"parameters\": {
                            \"type\": \"object\",
                            \"properties\": {
                                \"location\": {\"type\": \"string\", \"description\": \"城市名称\"}
                            },
                            \"required\": [\"location\"]
                        }
                    }
                },
                {
                    \"type\": \"function\",
                    \"function\": {
                        \"name\": \"get_news\",
                        \"description\": \"获取新闻\",
                        \"parameters\": {
                            \"type\": \"object\",
                            \"properties\": {
                                \"category\": {\"type\": \"string\", \"description\": \"新闻类别\"}
                            },
                            \"required\": [\"category\"]
                        }
                    }
                }
            ],
            \"tool_choice\": \"auto\"
        }")
    
    tool_code=$(echo "$tool_response" | tail -n1)
    tool_body=$(echo "$tool_response" | sed '$d')
    
    if [ "$tool_code" = "200" ]; then
        parallel_tool="✅"
        echo "  状态：✅ 支持并行工具调用"
    elif [ "$tool_code" = "400" ]; then
        error_msg=$(echo "$tool_body" | grep -o '"message"[^,}]*' | head -1 | cut -d'"' -f4)
        if echo "$error_msg" | grep -qi "single tool-calls\|parallel"; then
            parallel_tool="❌"
            echo "  状态：❌ 不支持并行工具调用"
            echo "  错误信息：$error_msg"
        else
            parallel_tool="⚠️"
            echo "  状态：⚠️ 其他错误"
            echo "  错误信息：$error_msg"
        fi
    else
        parallel_tool="❌"
        echo "  状态：❌ 请求失败 (HTTP $tool_code)"
        error_msg=$(echo "$tool_body" | grep -o '"message"[^,}]*' | head -1 | cut -d'"' -f4)
        echo "  错误：${error_msg:-未知错误}"
    fi
    
    # 保存到文件
    echo "${model_short}|${connectivity}|${resp_time}|${parallel_tool}" >> "$RESULTS_FILE"
    echo ""
done

# 输出汇总表格
echo "=========================================="
echo "【测试结果汇总】"
echo "=========================================="
echo ""
printf "| %-25s | %-8s | %-10s | %-12s |\n" "模型" "连通性" "响应时间" "并行工具调用"
printf "|%-27s|%-10s|%-12s|%-14s|\n" "---------------------------" "--------" "----------" "--------------"

while IFS='|' read -r model connectivity resp_time parallel_tool; do
    full_model="z-ai/$model"
    if [ "$model" = "chatglm3-6b" ]; then
        full_model="thudm/$model"
    fi
    printf "| %-25s | %-8s | %-10s | %-12s |\n" "$full_model" "$connectivity" "$resp_time" "$parallel_tool"
done < "$RESULTS_FILE"

echo ""
echo "=========================================="
echo "【汇总建议】"
echo "=========================================="
echo ""

while IFS='|' read -r model connectivity resp_time parallel_tool; do
    full_model="z-ai/$model"
    if [ "$model" = "chatglm3-6b" ]; then
        full_model="thudm/$model"
    fi
    
    if [ "$connectivity" = "✅" ] && [ "$parallel_tool" = "✅" ]; then
        echo "✅ $full_model - 推荐添加（连通性正常 + 支持并行工具调用）"
    elif [ "$connectivity" = "✅" ]; then
        echo "⚠️ $full_model - 可添加但有限制（连通性正常但不支持并行工具调用）"
    else
        echo "❌ $full_model - 不推荐（连通性测试失败）"
    fi
done < "$RESULTS_FILE"

echo ""
echo "测试完成！"
