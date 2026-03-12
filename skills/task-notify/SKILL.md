---
name: task-notify
description: Ensure long-running tasks actively notify the user instead of going silent. Use when handling work that may take more than ~30 seconds, especially exec background jobs, browser automation, sub-agent runs, downloads, file processing, transcription, or any task where the user might otherwise wonder whether work is still progressing.
---

# Task Notify

Use this skill to keep long-running work visible without creating noisy updates or large token overhead.

## Core rule

For any task likely to take **>30 seconds**:
1. Send a **start** update immediately.
2. Send **progress** updates only on meaningful milestones.
3. Send a **finish** update on success or failure.

Do not make the user ask whether the task is still running.

## Default cadence (low-cost mode)

Use the lightest acceptable cadence:
- **Start:** always
- **Progress:** every **2-3 minutes** at most, or at **25% / 50% / 75%**, whichever is more natural
- **Finish:** always

Avoid high-frequency updates. If nothing meaningful changed, do not send a progress message.

## Message shapes

Keep notifications short and concrete.

### Start
- task
- ETA range
- next update cadence

Example:
```text
🦞 任务已启动：正在整理 120 个文件，预计 5–10 分钟；我会每 2–3 分钟同步一次进度。
```

### Progress
- what changed
- elapsed time
- next expected checkpoint

Example:
```text
📊 进度更新：已完成约 50%（前 60 个文件已处理），已用 3 分钟；下一次在完成剩余扫描或 2–3 分钟后同步。
```

### Finish
- success/failure
- total time
- useful result summary
- next step when relevant

Example:
```text
✅ 已完成：共处理 120 个文件，耗时 7 分钟；结果已输出到 `out/report.json`。
```

## Task types

### 1) exec background jobs

For long shell commands:
- prefer wrapping with `scripts/longtask-run.sh`
- use a short label
- poll calmly; do not spam `process poll`
- forward heartbeat lines as compact human updates only when enough time has passed

Pattern:
```bash
scripts/longtask-run.sh --interval 150 label "build index" -- <command...>
```

Use `scripts/task-notify-state.py` to create/update/finish a local task-state entry when useful.

### 2) browser automation

Do **not** create progress updates by taking extra snapshots/screenshots just for status.

Instead:
- notify at workflow boundaries
- examples: "已登录", "已进入结果页", "正在下载", "正在整理结果"
- close non-essential tabs at the end unless the user asked to keep them

### 3) sub-agent runs

Do not assume sub-agents will naturally notify well.

When spawning a sub-agent for work that may take time:
- tell the user the sub-agent was launched
- state the expected duration
- ask the sub-agent to report only **major milestones** and the final result
- prefer **main-agent relay** over frequent direct chatter from the sub-agent
- append a notification block to the spawned task, or generate one with `scripts/build-subagent-task.py`

Use wording like:
```text
已启动子代理处理该任务；预计 10–20 分钟。我会在关键节点同步，不会刷屏。
```

Read `references/subagent-template.md` for the exact wrapper text and milestone shapes.

### 4) mixed workflows

If a task includes browser + shell + sub-agent steps, keep one task label and report by stage:
- stage 1/3: gathering
- stage 2/3: processing
- stage 3/3: summarizing

This is clearer and cheaper than many tiny updates.

## When not to notify repeatedly

Do not send repeated progress updates when:
- the task will finish in under ~30 seconds
- nothing materially changed
- you would only restate that work is still running
- the update would require expensive extra tool calls just to produce status

## Failure handling

On failure, always include:
- what failed
- the likely reason
- what was already tried
- the best next step

Keep it concise.

## Local state file

Optional local state file:
- path: `task-state.json` in workspace root
- use it for active/completed task tracking when a task has multiple stages or spans tools

Helper:
```bash
python3 skills/task-notify/scripts/task-notify-state.py start <id> "<label>" --eta "5-10m"
python3 skills/task-notify/scripts/task-notify-state.py progress <id> --progress 50 --note "已完成扫描"
python3 skills/task-notify/scripts/task-notify-state.py done <id> --result success --note "输出到 out/report.json"
```

## Practical defaults

- Default to **light mode**, not verbose mode.
- Prefer **fewer, better** updates.
- Prefer **tool state** over model-generated filler.
- Prefer **main-agent summaries** over noisy raw sub-agent updates.

## Bundled resources

- `scripts/task-notify-state.py` — maintain `task-state.json`
- `scripts/build-subagent-task.py` — wrap a sub-agent task with low-noise notification requirements
- `references/examples.md` — concrete patterns for exec, browser, and sub-agent tasks
- `references/subagent-template.md` — exact wording for sub-agent milestone reporting
