# Task Notify examples

## 1. exec 长任务

开始：
```text
🦞 任务已启动：正在执行批量转录，预计 10–20 分钟；我会每 2–3 分钟同步一次。
```

运行：
```bash
scripts/longtask-run.sh --interval 150 label "batch-transcribe" -- python3 transcribe.py
```

状态文件：
```bash
python3 skills/task-notify/scripts/task-notify-state.py start transcribe-001 "批量转录" --eta "10-20m" --kind exec
python3 skills/task-notify/scripts/task-notify-state.py progress transcribe-001 --progress 50 --note "已完成一半文件"
python3 skills/task-notify/scripts/task-notify-state.py done transcribe-001 --result success --note "输出到 out/"
```

## 2. 浏览器任务

推荐阶段：
- 已进入目标站点
- 已完成登录/确认登录态正常
- 已进入结果页
- 已开始提取
- 已整理完成

不要为了报进度额外多截图、多 snapshot。

## 3. 子代理任务

启动时告诉用户：
```text
🦞 已启动子代理处理该任务，预计 10–20 分钟；我会在关键节点同步，不会刷屏。
```

对子代理的任务描述里明确要求：
- 只在关键里程碑更新
- 完成时给出最终摘要
- 不要高频碎片化播报
- 优先由主代理转述给用户

可以直接用：
```bash
python3 skills/task-notify/scripts/build-subagent-task.py "检查最近 20 个 issue，并给出修复建议"
```

或参考：`references/subagent-template.md`

## 4. 失败通知

```text
❌ 任务失败：登录步骤通过了，但结果页提取不稳定；我已尝试重扫页面与候选规则，下一步建议改结果页选择器后再重试。
```
