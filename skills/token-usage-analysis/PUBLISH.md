# 📦 Token Usage Analysis - 发布指南

## ✅ 发布前检查清单

### 安全审计
- [x] 无 API Key / Token 泄露
- [x] 无密码/认证信息
- [x] 无个人邮箱/账号
- [x] 无硬编码路径（使用 $HOME 变量）
- [x] 无网络请求/外发数据
- [x] 无环境变量读取

**审计结果**: ✅ 通过（详见 `SECURITY_AUDIT.md`）

---

## 🚀 发布方式

### 方式 1：ClawHub 发布（推荐）

```bash
# 1. 进入技能目录
cd ~/.openclaw/workspace/skills/token-usage-analysis

# 2. 验证 clawhub.yaml
cat clawhub.yaml

# 3. 发布到 ClawHub
# 注意：需要 clawhub CLI 工具
clawhub publish .

# 或者通过网页上传
# 访问：https://clawhub.com/publish
# 上传整个目录
```

### 方式 2：打包分享

```bash
# 1. 打包技能
cd ~/.openclaw/workspace/skills/
tar -czf token-usage-analysis.tar.gz token-usage-analysis/

# 2. 分享给朋友
# 发送文件：token-usage-analysis.tar.gz

# 3. 朋友安装
tar -xzf token-usage-analysis.tar.gz -C ~/.openclaw/workspace/skills/
~/.openclaw/workspace/skills/token-usage-analysis/install.sh
```

### 方式 3：GitHub 仓库

```bash
# 1. 创建 GitHub 仓库
# https://github.com/your-username/token-usage-analysis

# 2. 推送代码
cd ~/.openclaw/workspace/skills/token-usage-analysis
git init
git add .
git commit -m "Initial release: token-usage-analysis v1.0.0"
git remote add origin https://github.com/your-username/token-usage-analysis.git
git push -u origin main

# 3. 分享仓库链接
# https://github.com/your-username/token-usage-analysis
```

---

## 📋 安装说明（给用户）

### 快速安装

```bash
# 方式 A：通过 ClawHub（如果已发布）
clawhub install token-usage-analysis

# 方式 B：手动安装
# 1. 下载技能包
# 2. 解压到 ~/.openclaw/workspace/skills/
# 3. 运行安装脚本
~/.openclaw/workspace/skills/token-usage-analysis/install.sh
```

### 验证安装

```bash
# 检查定时任务
# macOS
launchctl list | grep token-usage

# Linux
crontab -l | grep token-usage

# 手动触发收集
~/.openclaw/bin/collect-usage

# 诊断状态
~/.openclaw/bin/collect-usage --diagnose
```

---

## 📊 技能信息

- **名称**: token-usage-analysis
- **版本**: 1.0.0
- **作者**: 麻辣小龙虾 🦞
- **描述**: OpenClaw Token 用量分析工具
- **许可证**: MIT

### 功能
- ✅ 每小时自动收集 Token 用量
- ✅ 按 Agent/日期/时间范围分析
- ✅ 日志自动轮转（10MB + 90 天）
- ✅ 跨平台支持（macOS/Linux）

### 系统要求
- Python 3.7+
- macOS 或 Linux
- OpenClaw 0.9.0+

---

## 🔒 安全声明

本技能已通过安全审计，确认：
- 不读取任何 API Key 或认证信息
- 不访问网络
- 不外发任何数据
- 仅读取本地 session 文件中的 usage 字段
- 日志文件仅包含用量统计，不含对话内容

详细审计报告：`SECURITY_AUDIT.md`

---

## 📝 更新日志

### v1.0.0 (2026-03-09)
- 初始版本发布
- 支持每小时自动收集
- 支持多维度用量分析
- 支持日志自动轮转和清理

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

仓库地址：（待添加）

---

## 📞 支持

遇到问题？
1. 运行诊断：`collect-usage --diagnose`
2. 查看日志：`~/.openclaw/logs/token-usage-collector.log`
3. 提交 Issue：（待添加）
