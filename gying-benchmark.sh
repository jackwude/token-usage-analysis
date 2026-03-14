#!/bin/bash
# GYING A/B 基准测试脚本
# 比较 Profile 专用方案 vs Agent Browser State 方案

set -euo pipefail

RESULTS_DIR="$HOME/.openclaw/workspace/benchmark-results"
mkdir -p "$RESULTS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROFILE_RESULTS="$RESULTS_DIR/profile_scheme_$TIMESTAMP.json"
STATE_RESULTS="$RESULTS_DIR/state_scheme_$TIMESTAMP.json"

ROUNDS=5
KEYWORD="寻秦记"

log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

get_ms() {
    echo $(($(date +%s%N)/1000000))
}

# ============== 方案 A: Profile 专用 ==============
test_profile_scheme() {
    local round=$1
    local result_file="$RESULTS_DIR/profile_round_${round}_$(date +%s).json"
    
    log "【Profile 方案】第 $round 轮测试开始"
    
    # 1. 启动 Chrome (后台)
    PROFILE_DIR="$HOME/.openclaw/chrome-profiles/gying"
    CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    DEBUG_PORT="9224"
    
    # 确保没有残留进程
    pkill -f "user-data-dir.*gying" 2>/dev/null || true
    sleep 1
    
    # 启动 Chrome
    "$CHROME_BIN" \
      --user-data-dir="$PROFILE_DIR" \
      --profile-directory=Default \
      --no-first-run \
      --disable-blink-features=AutomationControlled \
      --disable-features=TranslateUI \
      --disable-component-extensions-with-background-pages \
      --disable-default-apps \
      --disable-sync \
      --remote-debugging-port="$DEBUG_PORT" \
      "https://www.gying.net/" &
    
    local chrome_pid=$!
    log "Chrome 启动 (PID: $chrome_pid)"
    
    # 等待 CDP 端口可用
    sleep 2
    for i in {1..10}; do
        if curl -s "http://127.0.0.1:$DEBUG_PORT/json/version" >/dev/null 2>&1; then
            log "CDP 端口就绪"
            break
        fi
        sleep 1
    done
    
    local t0=$(get_ms)
    
    # 2. 连接并等待首页可交互
    local home_ready=0
    for i in {1..30}; do
        if agent-browser --cdp $DEBUG_PORT snapshot 2>/dev/null | grep -q "观影网\|GYING\|搜索" ; then
            home_ready=$(get_ms)
            log "首页可交互 (耗时: $((home_ready - t0))ms)"
            break
        fi
        sleep 0.5
    done
    
    if [ $home_ready -eq 0 ]; then
        home_ready=$(get_ms)
        log "⚠️ 首页超时，使用当前时间"
    fi
    
    local home_time=$((home_ready - t0))
    
    # 3. 执行搜索
    # 找到搜索框并输入关键词
    agent-browser --cdp $DEBUG_PORT fill 'input[placeholder*="搜索"], input[type="search"], #search-input' "$KEYWORD" 2>/dev/null || \
    agent-browser --cdp $DEBUG_PORT keyboard type "$KEYWORD" 2>/dev/null || true
    
    sleep 0.5
    
    # 按回车
    agent-browser --cdp $DEBUG_PORT press Enter 2>/dev/null || true
    
    local search_start=$(get_ms)
    
    # 4. 等待搜索结果
    local search_ready=0
    for i in {1..30}; do
        local snapshot=$(agent-browser --cdp $DEBUG_PORT snapshot 2>/dev/null || echo "")
        if echo "$snapshot" | grep -qi "寻秦记\|结果\|集\|季" ; then
            search_ready=$(get_ms)
            log "搜索结果可读 (耗时: $((search_ready - search_start))ms)"
            break
        fi
        sleep 0.5
    done
    
    if [ $search_ready -eq 0 ]; then
        search_ready=$(get_ms)
        log "⚠️ 搜索结果超时"
    fi
    
    local search_time=$((search_ready - search_start))
    local total_time=$((search_ready - t0))
    
    # 5. 记录结果
    cat > "$result_file" <<EOF
{
    "round": $round,
    "scheme": "profile",
    "home_time_ms": $home_time,
    "search_time_ms": $search_time,
    "total_time_ms": $total_time,
    "timestamp": "$(date -Iseconds)",
    "success": $([ $home_time -lt 15000 ] && echo "true" || echo "false")
}
EOF
    
    # 6. 清理
    pkill -f "user-data-dir.*gying" 2>/dev/null || true
    sleep 1
    
    log "【Profile 方案】第 $round 轮完成 - 总耗时: ${total_time}ms"
    
    echo "$home_time,$search_time,$total_time"
}

# ============== 方案 B: State 方案 ==============
test_state_scheme() {
    local round=$1
    local result_file="$RESULTS_DIR/state_round_${round}_$(date +%s).json"
    
    log "【State 方案】第 $round 轮测试开始"
    
    local t0=$(get_ms)
    
    # 使用 session-name 自动保存/恢复状态
    export AGENT_BROWSER_SESSION_NAME="gying-benchmark-state"
    
    # 1. 打开首页
    agent-browser --session-name "$AGENT_BROWSER_SESSION_NAME" open "https://www.gying.net/" >/dev/null 2>&1 &
    local browser_pid=$!
    
    # 等待首页可交互
    local home_ready=0
    for i in {1..30}; do
        sleep 0.5
        if agent-browser --session-name "$AGENT_BROWSER_SESSION_NAME" snapshot 2>/dev/null | grep -q "观影网\|GYING\|搜索" ; then
            home_ready=$(get_ms)
            log "首页可交互 (耗时: $((home_ready - t0))ms)"
            break
        fi
    done
    
    if [ $home_ready -eq 0 ]; then
        home_ready=$(get_ms)
        log "⚠️ 首页超时"
    fi
    
    local home_time=$((home_ready - t0))
    
    # 2. 执行搜索
    agent-browser --session-name "$AGENT_BROWSER_SESSION_NAME" fill 'input[placeholder*="搜索"], input[type="search"]' "$KEYWORD" 2>/dev/null || \
    agent-browser --session-name "$AGENT_BROWSER_SESSION_NAME" keyboard type "$KEYWORD" 2>/dev/null || true
    
    sleep 0.5
    agent-browser --session-name "$AGENT_BROWSER_SESSION_NAME" press Enter 2>/dev/null || true
    
    local search_start=$(get_ms)
    
    # 3. 等待搜索结果
    local search_ready=0
    for i in {1..30}; do
        sleep 0.5
        local snapshot=$(agent-browser --session-name "$AGENT_BROWSER_SESSION_NAME" snapshot 2>/dev/null || echo "")
        if echo "$snapshot" | grep -qi "寻秦记\|结果\|集\|季" ; then
            search_ready=$(get_ms)
            log "搜索结果可读 (耗时: $((search_ready - search_start))ms)"
            break
        fi
    done
    
    if [ $search_ready -eq 0 ]; then
        search_ready=$(get_ms)
        log "⚠️ 搜索结果超时"
    fi
    
    local search_time=$((search_ready - search_start))
    local total_time=$((search_ready - t0))
    
    # 4. 记录结果
    cat > "$result_file" <<EOF
{
    "round": $round,
    "scheme": "state",
    "home_time_ms": $home_time,
    "search_time_ms": $search_time,
    "total_time_ms": $total_time,
    "timestamp": "$(date -Iseconds)",
    "success": $([ $home_time -lt 15000 ] && echo "true" || echo "false")
}
EOF
    
    # 5. 清理浏览器
    pkill -f "agent-browser" 2>/dev/null || true
    sleep 1
    
    log "【State 方案】第 $round 轮完成 - 总耗时: ${total_time}ms"
    
    echo "$home_time,$search_time,$total_time"
}

# ============== 主测试流程 ==============
main() {
    log "=========================================="
    log "GYING A/B 基准测试开始"
    log "轮次数：$ROUNDS"
    log "关键词：$KEYWORD"
    log "=========================================="
    
    # 方案 A 测试
    log ""
    log "========== 方案 A: Profile 专用 =========="
    PROFILE_DATA=""
    for i in $(seq 1 $ROUNDS); do
        result=$(test_profile_scheme $i)
        if [ -n "$PROFILE_DATA" ]; then
            PROFILE_DATA="$PROFILE_DATA"$'\n'"$result"
        else
            PROFILE_DATA="$result"
        fi
        sleep 2
    done
    
    # 方案 B 测试
    log ""
    log "========== 方案 B: State 方案 =========="
    STATE_DATA=""
    for i in $(seq 1 $ROUNDS); do
        result=$(test_state_scheme $i)
        if [ -n "$STATE_DATA" ]; then
            STATE_DATA="$STATE_DATA"$'\n'"$result"
        else
            STATE_DATA="$result"
        fi
        sleep 2
    done
    
    # 保存原始数据
    echo "$PROFILE_DATA" > "$RESULTS_DIR/profile_raw_$TIMESTAMP.csv"
    echo "$STATE_DATA" > "$RESULTS_DIR/state_raw_$TIMESTAMP.csv"
    
    log ""
    log "=========================================="
    log "测试完成！原始数据已保存到 $RESULTS_DIR"
    log "=========================================="
    
    # 输出数据供后续分析
    echo "PROFILE_DATA_START"
    echo "$PROFILE_DATA"
    echo "PROFILE_DATA_END"
    echo "STATE_DATA_START"
    echo "$STATE_DATA"
    echo "STATE_DATA_END"
}

main "$@"
