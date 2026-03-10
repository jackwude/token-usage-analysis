#!/bin/bash
# OpenClaw Session Usage Logger (每小时记录)
# 记录当前活跃 session 的 Token 用量信息

LOG_FILE="$HOME/.openclaw/logs/session-usage.log"
MAX_SIZE=$((10 * 1024 * 1024))  # 10MB

# 检查日志大小
if [ -f "$LOG_FILE" ]; then
    size=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
    if [ "$size" -ge "$MAX_SIZE" ]; then
        echo "⚠️ 警告：session-usage.log 已达到 10MB，需要清理！"
    fi
fi

# 获取当前时间
timestamp=$(date -Iseconds)

# 列出最近活跃的 session 文件
sessions_dir="$HOME/.openclaw/agents/main/sessions"
if [ -d "$sessions_dir" ]; then
    # 找出最近 2 小时内修改过的 jsonl 文件
    find "$sessions_dir" -name "*.jsonl" -type f -mmin -120 | while read file; do
        session_id=$(basename "$file" .jsonl)
        mtime=$(stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%S" "$file" 2>/dev/null || stat -c "%y" "$file" 2>/dev/null | cut -d' ' -f1,2 | tr ' ' 'T')
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        
        # 从 session 文件中提取 Token 用量 (累加所有消息的 usage)
        tokens_in=0
        tokens_out=0
        total_cost=0
        
        # 使用 grep + sed 提取 usage 字段并累加
        while IFS= read -r line; do
            if echo "$line" | grep -q '"usage"'; then
                # 提取 input tokens
                input=$(echo "$line" | grep -o '"input":[0-9]*' | head -1 | cut -d':' -f2)
                # 提取 output tokens
                output=$(echo "$line" | grep -o '"output":[0-9]*' | head -1 | cut -d':' -f2)
                # 提取 total cost
                cost=$(echo "$line" | grep -o '"total":[0-9.]*' | head -1 | cut -d':' -f2)
                
                [ -n "$input" ] && tokens_in=$((tokens_in + input))
                [ -n "$output" ] && tokens_out=$((tokens_out + output))
                [ -n "$cost" ] && total_cost=$(echo "$total_cost + $cost" | bc 2>/dev/null || echo "$total_cost")
            fi
        done < "$file"
        
        # 获取当前使用的模型
        model=$(grep -o '"model":"[^"]*"' "$file" | tail -1 | cut -d'"' -f4)
        [ -z "$model" ] && model="unknown"
        
        echo "$timestamp | session=$session_id | model=$model | tokens_in=$tokens_in | tokens_out=$tokens_out | cost=\$$total_cost | file_size=$size" >> "$LOG_FILE"
        # 静默模式，不输出通知
    done
else
    echo "⚠️ Sessions 目录不存在：$sessions_dir"
fi
