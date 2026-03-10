# Long tasks: anti-silence protocol (方案 1 + 方案 2 最小看门狗)

## Goal
Prevent the "agent seems dead" experience during long-running work.

This repo implements:
- **方案 1（行为层）**: Always do start/progress/end messaging.
- **方案 2（最小看门狗）**: A local wrapper (`scripts/longtask-run.sh`) that emits periodic heartbeats to stdout so the agent can poll and forward them to the user when a command might run for a long time.

> Note: The watchdog here is deliberately minimal and **does not** send messages by itself (avoids adding a new outbound channel / permissions). It's a *mechanical guarantee* that there is always fresh progress text available.

## How to use (agent/operator)

### 1) Before starting a long task
Send immediately:
- what I'm doing
- ETA range
- update cadence (every 2–3 minutes)

### 2) When running a long shell command
Run it via:

```bash
scripts/longtask-run.sh --interval 150 label "<short label>" -- <command...>
```

Then, while it runs, poll output (OpenClaw `process(action=poll)`), and forward any `[longtask] heartbeat` lines to the chat.

### 3) On finish
Forward the `[longtask] done ...` line + the actual result summary.

## Rollback
- This feature is self-contained to `scripts/longtask-run.sh` + this doc.
- Remove the files or revert the commit.
- `config/longtask-watchdog.json` exists as a placeholder for future automation and defaults to `enabled:false`.

## Safety / stability notes
- No background daemons.
- No cron.
- No changes to OpenClaw core config.
- Only affects tasks where the wrapper is used.
