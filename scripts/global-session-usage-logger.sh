#!/bin/bash
# OpenClaw Global Session Usage Logger (每小时记录)
# 目标：遍历 ~/.openclaw/agents/*/sessions 下最近活跃的 session，记录各 session 的累计 Token/Cost
# 用途：后续可按 session 计算相邻两次快照的差值，从而得到“每小时增量消耗”，并可汇总到 agent 维度。

set -euo pipefail

LOG_FILE="$HOME/.openclaw/logs/session-usage.log"
MAX_SIZE=$((10 * 1024 * 1024))  # 10MB

# 检查日志大小
if [ -f "$LOG_FILE" ]; then
  size=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
  if [ "$size" -ge "$MAX_SIZE" ]; then
    echo "⚠️ 警告：session-usage.log 已达到 10MB，需要清理！" >&2
  fi
fi

timestamp=$(date -Iseconds)

agents_root="$HOME/.openclaw/agents"
if [ ! -d "$agents_root" ]; then
  echo "⚠️ agents 目录不存在：$agents_root" >&2
  exit 0
fi

# 遍历所有 agent 的 sessions
find "$agents_root" -mindepth 1 -maxdepth 1 -type d | while read -r agent_dir; do
  agent_id=$(basename "$agent_dir")
  sessions_dir="$agent_dir/sessions"
  [ -d "$sessions_dir" ] || continue

  # 找出最近 2 小时内修改过的 jsonl 文件
  find "$sessions_dir" -name "*.jsonl" -type f -mmin -120 | while read -r file; do
    session_id=$(basename "$file" .jsonl)
    mtime=$(stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%S" "$file" 2>/dev/null || stat -c "%y" "$file" 2>/dev/null | cut -d' ' -f1,2 | tr ' ' 'T' || echo "unknown")
    fsize=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)

    tokens_in=0
    tokens_out=0
    total_cost=0

    # 累加 usage（session 文件里 usage 是按消息记录的）
    # 新格式："usage":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0,"totalTokens":0,"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0,"total":0}}
    while IFS= read -r line; do
      if echo "$line" | grep -q '"usage"'; then
        # 提取 usage 对象内容
        usage_part=$(echo "$line" | grep -o '"usage":{[^}]*}' | head -1 || true)
        if [ -n "${usage_part:-}" ]; then
          input=$(echo "$usage_part" | grep -o '"input":[0-9]*' | head -1 | cut -d':' -f2 || true)
          output=$(echo "$usage_part" | grep -o '"output":[0-9]*' | head -1 | cut -d':' -f2 || true)
          # cost 是嵌套对象，提取 cost.total
          cost=$(echo "$line" | grep -o '"cost":{[^}]*}' | head -1 | grep -o '"total":[0-9.]*' | head -1 | cut -d':' -f2 || true)
        else
          # 旧格式兜底
          input=$(echo "$line" | grep -o '"input":[0-9]*' | head -1 | cut -d':' -f2 || true)
          output=$(echo "$line" | grep -o '"output":[0-9]*' | head -1 | cut -d':' -f2 || true)
          cost=$(echo "$line" | grep -o '"total":[0-9.]*' | head -1 | cut -d':' -f2 || true)
        fi

        [ -n "${input:-}" ] && tokens_in=$((tokens_in + input))
        [ -n "${output:-}" ] && tokens_out=$((tokens_out + output))
        if [ -n "${cost:-}" ]; then
          total_cost=$(echo "$total_cost + $cost" | bc 2>/dev/null || echo "$total_cost")
        fi
      fi
    done < "$file"

    # 获取模型（优先 model_change.modelId，其次 message 里 model 字段兜底）
    model=$(grep -o '"modelId":"[^"]*"' "$file" | tail -1 | cut -d'"' -f4 || true)
    if [ -z "${model:-}" ]; then
      model=$(grep -o '"model":"[^"]*"' "$file" | tail -1 | cut -d'"' -f4 || true)
    fi
    [ -z "${model:-}" ] && model="unknown"

    echo "$timestamp | agent=$agent_id | session=$session_id | model=$model | tokens_in=$tokens_in | tokens_out=$tokens_out | cost=\$$total_cost | file_mtime=$mtime | file_size=$fsize" >> "$LOG_FILE"
  done
done
