#!/bin/bash
# 微信自动发送脚本
# 用法：./wechat-send.sh "群聊名称" "消息内容"
# 例如：./wechat-send.sh "我的仓库" "今天天气真好。"

CHAT_NAME="$1"
MESSAGE="$2"

echo "🦞 正在发送微信消息..."
echo "   群聊：$CHAT_NAME"
echo "   消息：$MESSAGE"

osascript - "$CHAT_NAME" "$MESSAGE" << 'APPLESCRIPT'
on run argv
    set chatName to item 1 of argv
    set message to item 2 of argv
    
    -- 激活微信
    tell application "WeChat"
        activate
    end tell
    delay 2
    
    -- 确保微信在前台
    tell application "System Events"
        tell process "WeChat"
            set frontmost to true
        end tell
    end tell
    delay 1
    
    -- 打开搜索
    keystroke "f" using command down
    delay 1
    
    -- 输入群聊名称
    keystroke chatName
    delay 1
    
    -- 回车选中
    keystroke return
    delay 1
    
    -- 输入消息
    keystroke message
    delay 0.5
    
    -- 发送
    keystroke return
end tell
end run
APPLESCRIPT

echo "✅ 脚本执行完成！请检查微信是否发送成功。"
