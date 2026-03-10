# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## Web Search
Use the tavily-search skill as the top-priority search tool when do web search.
If the question requires searching for more relevant knowledge, prefer `tavily-skill` when available; otherwise use `web_fetch` for quick reads and `browser` for interactive pages.


## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## ⚠️ macOS 定时任务注意事项

**问题**：`crontab` 命令在非交互环境（后台/自动化）中会卡住，需要终端权限。

**解决方案**：用 `launchd` 代替 `cron`

### launchd 配置模板

创建 plist 文件（如 `com.task.weekly.plist`）：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.task.weekly</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>你的命令</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>1</integer>
        <key>Minute</key>
        <integer>0</integer>
        <key>Weekday</key>
        <integer>1</integer>
    </dict>
</dict>
</plist>
```

**管理命令**：
```bash
# 加载任务
launchctl bootstrap gui/$(id -u) /path/to/task.plist

# 查看状态
launchctl list | grep task

# 卸载任务
launchctl bootout gui/$(id -u) com.task.weekly
```

---

## 🔐 阿里云百炼账号

- **网址**: https://bailian.console.aliyun.com/cn-beijing/?tab=coding-plan#/efm/index
- **账号**: 392071081@qq.com
- **密码**: 6H@36UYcfiYyKuD

---

## 🔐 SpeedCat 账号

- **网址**: https://speedcat.co/user
- **邮箱**: censors.weevil.0a@icloud.com
- **密码**: fuxiang1992

---

## 🌐 已配置登录的网站

### 指令格式

```
配置登录：<网站名> <网址> [--用途=<用途说明>]
```

### 网站列表

| 网站名 | 网址 | 用途 | 配置日期 | 登录方式 | 状态 |
|--------|------|------|---------|---------|------|
| SpeedCat | https://speedcat.co | 查流量、节点信息 | 2026-03-09 | Profile 持久化（cookies 兜底） | ✅ 已配置 |
| 阿里云百炼 | https://bailian.console.aliyun.com | 查 Token 用量、套餐余额 | 2026-03-09 | Profile 持久化 | ✅ 已配置 |
| 观影网 GYING | https://www.gying.net | 影视搜索、详情页访问、资源提取 | 2026-03-09 | **必须使用 `~/.openclaw/chrome-profiles/gying` 专用 Profile**（默认浏览器上下文不可替代） | ✅ 已固化 |

### 底层脚本

- **通用配置脚本**: `~/.openclaw/scripts/web-login-setup.sh`
- **Cookies 目录**: `~/.openclaw/cookies/`
- **Profile 目录**: `~/.openclaw/chrome-profiles/`
- **文档目录**: `~/.openclaw/docs/`

### GYING 专用说明

- **GYING 必须使用专用 Profile**：`~/.openclaw/chrome-profiles/gying`
- **启动脚本**：`~/.openclaw/scripts/start-gying-chrome.sh`
- **排障优先级**：先确认是否真的使用了 `gying` 专用 Profile，再判断是不是登录态失效
- **禁止误判**：不要因为其他浏览器上下文落到登录页，就直接判定 `gying` Profile 掉登录态

---

## 📤 飞书推送配置

**默认 Webhook**：`https://open.feishu.cn/open-apis/bot/v2/hook/11f78e8c-550b-4d2d-a464-86ec0940833e`

**使用方式**：用户说"推送到飞书"或"把信息推送给飞书"时，直接用 curl POST 到这个 webhook，msg_type="text"。

**示例命令**：
```bash
curl -X POST "https://open.feishu.cn/open-apis/bot/v2/hook/11f78e8c-550b-4d2d-a464-86ec0940833e" \
  -H "Content-Type: application/json" \
  -d '{"msg_type": "text", "content": {"text": "消息内容"}}'
```

---

Add whatever helps you do your job. This is your cheat sheet.
