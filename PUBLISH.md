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

## 📌 当前发布信息

- **名称**: token-usage-analysis
- **版本**: 1.1.0
- **仓库**: https://github.com/jackwude/token-usage-analysis
- **分支**: main
- **定位**: 自动收集 + 对话式分析 OpenClaw Token 用量

---

## 🚀 发布方式

### 方式 1：ClawHub 发布（推荐）

```bash
# 1. 进入技能目录
cd ~/.openclaw/workspace/skills/token-usage-analysis

# 2. 检查元信息
cat clawhub.yaml

# 3. 发布到 ClawHub
clawhub publish .
```

### 方式 2：GitHub 仓库

```bash
cd ~/.openclaw/workspace/skills/token-usage-analysis
git push origin main
```

### 方式 3：打包分享

```bash
cd ~/.openclaw/workspace/skills/
tar -czf token-usage-analysis.tar.gz token-usage-analysis/
```

---

## 📋 安装说明（给用户）

### GitHub 安装

```bash
git clone https://github.com/jackwude/token-usage-analysis.git ~/.openclaw/workspace/skills/token-usage-analysis
~/.openclaw/workspace/skills/token-usage-analysis/install.sh
```

### 验证安装

```bash
~/.openclaw/bin/collect-usage --diagnose
~/.openclaw/bin/collect-usage
python3 ~/.openclaw/workspace/skills/token-usage-analysis/src/analyzer.py 7d
```

---

## 📊 版本亮点

### v1.1.0 (2026-03-11)
- ✅ 重构为**对话优先**模式
- ✅ 固化五段式结果输出模板
- ✅ 新增 `【7 天趋势图】` 文本柱状图
- ✅ 新增异常提示与一句话判断
- ✅ README / SKILL / 输出模板文档同步
- ✅ 新增 `.gitignore`，忽略 Python 缓存文件

### v1.0.0 (2026-03-09)
- 初始版本发布
- 支持每小时自动收集
- 支持多维度用量分析
- 支持日志自动轮转和清理

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

## 📞 支持

遇到问题：
1. 运行诊断：`collect-usage --diagnose`
2. 查看日志：`~/.openclaw/logs/token-usage-collector.log`
3. 仓库地址：https://github.com/jackwude/token-usage-analysis
4. Issue 页面：https://github.com/jackwude/token-usage-analysis/issues
