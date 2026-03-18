# LONGTASK_NOTIFY_V2

长任务通知默认执行骨架（方案 2：平衡模式）。

## 目标

- 不静默：开始必回
- 不刷屏：仅关键里程碑 25/50/75
- 不漏报：结束通知 finally 兜底

## 标准流程

1. 生成 `task_id`（唯一）
2. `task-state start`
3. 发送开始通知（任务 + ETA + 汇报节奏）
4. 执行任务
5. 到达 25/50/75 里程碑时发送进度（去抖：每里程碑最多一次，建议最短间隔 90s）
6. 任务退出时统一 `finish`（success/failed/timeout/interrupted）
7. 清理资源（浏览器 tab / 临时文件等）

## 子代理任务附加块（建议直接拼接到 spawn task）

```text
Notification requirements:
- This task is user-visible and may take time.
- Report only major milestones: start, 25%, 50%, 75%, and final.
- If no meaningful change, do not send progress updates.
- Final response must include: outcome, elapsed time (if known), key outputs/paths, and next step.
- On failure, include: likely cause, what you already tried, and best next action.
```

## Shell 任务建议

- 长命令优先：

```bash
scripts/longtask-run.sh --interval 150 label "<task-label>" -- <command...>
```

- 状态追踪：

```bash
python3 skills/task-notify/scripts/task-notify-state.py start <id> "<label>" --eta "5-10m"
python3 skills/task-notify/scripts/task-notify-state.py progress <id> --progress 25 --note "阶段说明"
python3 skills/task-notify/scripts/task-notify-state.py progress <id> --progress 50 --note "阶段说明"
python3 skills/task-notify/scripts/task-notify-state.py progress <id> --progress 75 --note "阶段说明"
python3 skills/task-notify/scripts/task-notify-state.py done <id> --result success --note "结果摘要"
```

## 文案模板

- 开始：`🦞 已启动：{label}；预计 {eta}；我会在 25/50/75 和结束时同步。`
- 进度：`📊 进度：{percent}%（{note}），已用时 {elapsed}。`
- 完成：`✅ 已完成：{label}，耗时 {elapsed}；结果：{summary}。`
- 失败：`❌ 失败：{label}，耗时 {elapsed}；原因：{reason}；已尝试：{tried}；建议：{next_step}。`
