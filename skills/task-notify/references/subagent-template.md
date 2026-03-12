# Sub-agent notify template

Use this template when spawning a sub-agent for work that may take more than ~30 seconds.

## Goal

Keep the user informed with **low-frequency, milestone-based** updates.
Do not spam. Do not send filler. Prefer concise milestone reports.

## Recommended wrapper text

Append guidance like this to the sub-agent task:

```text
Notification requirements:
- This task is user-visible and may take time.
- Report only major milestones, not every small action.
- Preferred cadence: at most every 2-3 minutes, or on meaningful milestones such as 25% / 50% / 75% / final.
- Good milestone examples: environment ready, data gathered, processing started, processing finished, result packaged, blocked on X.
- If there is no meaningful change, do not send a progress update.
- Final response must include: outcome, total time if known, key outputs/paths, and next recommended step.
- Keep updates short and practical.
```

## Preferred milestone shapes

### Start
```text
子代理已接手，正在准备环境 / 收集输入。
```

### Progress
```text
已完成数据收集，正在进入处理阶段；当前无阻塞。
```

### Blocked
```text
遇到阻塞：登录态失效 / 依赖缺失 / 结果页结构变化；我已尝试 X，下一步准备 Y。
```

### Finish
```text
已完成；输出为 `out/report.json`，关键结论为……；如需我继续，我建议下一步……
```

## Main-agent relay rule

Prefer this pattern:
- sub-agent sends sparse milestone updates
- main agent relays compact summaries to the user

This keeps the channel readable and reduces token waste.
